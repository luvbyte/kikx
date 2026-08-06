import os
import pwd
import sys
import logging
import asyncio
import shlex
import signal
from pathlib import Path
from fastapi import APIRouter, Request, Depends

from lib.utils import generate_uuid, joinpath
from lib.parser import parse_config
from lib.service import create_service

from typing import Any
from pydantic import BaseModel



logger = logging.getLogger(__name__)


srv = create_service(__file__, "Micro services")

# -------------- Models

class ServiceModel(BaseModel):
  name: str

class ServiceConfig(BaseModel):
  cmd: str
  shell: bool = False
  cwd: str = "{data}"
  forever: bool = False

def get_app(request: Request):
  _, app = srv.get_client_app(request)

  if not app.config.micro:
    srv.exception(403, "Permission denied.")

  return app

# -------------- Services

class SafeDict(dict):
  def __missing__(self, key: str) -> str:
    return '{' + key + '}'

class MService:
  def __init__(self, name: str, app: Any) -> None:
    self.name: str = name
    self.options: ServiceConfig = parse_config(joinpath(app.get_app_path() / "micro", f"{self.name}.json"), ServiceConfig)

    self.app_id: str = app.id
    self.sudo: bool = app.is_sudo
    self.app_name: str = app.name

    self.uid: str = generate_uuid()

    self.output: list[str] = []
    self.error_text: str = None
    self.started: bool = False
    self.completed: bool = False
    self._cleaned: bool = False

    self.env: dict[str, str] = os.environ.copy()

    self.cwd: str = self.options.cwd.format_map(SafeDict({
      "data": str(app.get_app_data_path())
    }))

    if not Path(self.cwd).is_dir():
      srv.exception(404, "Working directory not found")

    self.cmd: str = self.options.cmd.format_map(SafeDict({
      "data": str(app.get_app_data_path()),
    }))
    
    self.env.update({
      "KIKX_APP_ID": app.id,
      "KIKX_APP_NAME": app.name,
      "KIKX_STORAGE_PATH": str(app.user.storage_path),
      "KIKX_APP_PATH": str(app.get_app_path()),
      "KIKX_APP_DATA_PATH": str(app.get_app_data_path()),
      "KIKX_HOME_PATH": str(app.get_home_path())
    })
    
    self.env.update({
      # 1. app/bin | 2. storage/bin | 3. kikx path
      "PATH": f'{str(app.app_path / "bin")}:{app.user.get_path_env()}:{str(Path(sys.executable).parent)}:{self.env.get("PATH", "")}'
    })

    self.process: asyncio.subprocess.Process | None = None
    self.sid: int | None = None
    self.pgid: int | None = None

  def info(self) -> dict:
    return {
      "uid": self.uid,
      "app": {
        "id": self.app_id,
        "name": self.app_name,
        "sudo": self.sudo
      },
      "status": {
        "started": self.started,
        "completed": self.completed
      },
      "process": {
        "cmd": self.cmd,
        "cwd": self.cwd,
        "shell": self.shell,
        "returncode": self.returncode,
        "error": self.error_text
      },
      "is_forever": self.is_forever
    }

  @property
  def returncode(self) -> int | None:
    return None if self.process is None else self.process.returncode

  @property
  def shell(self) -> bool:
    return self.options.shell

  @property
  def is_forever(self) -> bool:
    return self.options.forever

  def get_user(self) -> str:
    return "root" if self.sudo else "nobody"

  def demote(self, user_name: str):
    def result():
      pw = pwd.getpwnam(user_name)
      os.setgid(pw.pw_gid)
      os.setuid(pw.pw_uid)
    return result

  def _create_process(self) -> asyncio.subprocess.Process:
    if self.sudo:
      preexec = None  # stay root
    else:
      preexec = self.demote(self.get_user())

    if self.shell:
      return asyncio.create_subprocess_shell(
        self.cmd,
        env=self.env,
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec,
        limit=10 * 1024 * 1024 # 10 mb
      )
    else:
      return asyncio.create_subprocess_exec(
        *shlex.split(self.cmd),
        env=self.env,
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec,
        limit=10 * 1024 * 1024 # 10 mb
      )

  # Start
  async def run(self) -> None:
    self.process = await self._create_process()
    self.started = True
    self._cleaned = False
    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)
  
    while True:
      try:
        stdout_line = await asyncio.wait_for(self.process.stdout.readline(), timeout=30)
        if not stdout_line:
          break

        self.output.append(stdout_line.decode())
      except asyncio.TimeoutError:
        if self.process.returncode is not None:
          break

    await self.process.wait()

    stderr = await self.process.stderr.read()
    if stderr:
      self.error_text = stderr.decode()

    self.completed = True
    
    return self.uid
  
  def get_output(self) -> list[str]:
    return self.output
  
  async def send(self, data: str) -> None:
    if not self.process or self.process.returncode is not None:
      return

    self.process.stdin.write(data.encode() + b'\n')
    await self.process.stdin.drain()

  def _force_kill(self) -> None:
    if (
      self.process is None
      or self.process.returncode is not None
      or self.pgid is None
    ):
      logger.info(f"Task {self.id} already finished or not fully started")
      return

    try:
      os.killpg(self.pgid, signal.SIGKILL)
    except ProcessLookupError:
      pass

  # Kill task
  def clean(self) -> None:
    if self._cleaned:
      return
    self._force_kill()
    self._cleaned = True


class MicroServices:
  def __init__(self) -> None:
    self._active: dict[str, MService] = {}
  
  # Get service or raise
  def get_service(self, uid: str) -> MService:
    service = self._active.get(uid)
    if not service:
      srv.exception(404, "Service not found")

    return service

  # Get services by name
  def get_active_services(self, app_name: str) -> list[dict]:
    return [s.info() for s in self._active.values() if s.app_name == app_name]

  def _task_done(self, uid: str) -> None:
    pass

  # Start service
  async def start_sevice(self, app: Any, name: str) -> dict:
    service = next(
      (s for s in self._active.values() if s.name == name),
      None,
    )
    if service:
      return service.info()

    service = MService(name, app)
    
    self._active[service.uid] = service

    task = asyncio.create_task(service.run())
    task.add_done_callback(self._task_done)

    logger.info(f"Micro({app.name}) start with {service.info()}")

    return service.info()
  
  # Stop service
  def stop_service(self, uid: str) -> None:
    service = self._active.pop(uid, None)
    if service:
      service.clean()
      
      logger.info(f"Micro(Stopped) {uid}, {service.app_name}")

  # Stop services by app_name
  def stop_services(self, app_name: str, force: bool = False) -> None:
    services = [s for s in self._active.values() if s.app_name == app_name]
    for s in services:
      # If forever tasks
      if s.is_forever and not force:
        continue
      self.stop_service(s.uid)

  # on app close
  def on_close_app(self, app_id: str, app_name: str) -> None:
    self.stop_services(app_name)

  # Stop services on shutdown
  def on_close(self) -> None:
    for s in self._active.values():
      s.clean()


micro = MicroServices()


@srv.on("startup")
def startup(core) -> None:
  core.events.add_event("app:close", micro.on_close_app)

@srv.on("shutdown")
def shutdown(_) -> None:
  micro.on_close()

# -------------- ROUTES

@srv.router.get("/list")
def get_active_services(request: Request, app = Depends(get_app)):
  return micro.get_active_services(app.name)

@srv.router.post("/start")
async def start_service(request: Request, payload: ServiceModel, app = Depends(get_app)):
  # Get App / Client
  return await micro.start_sevice(app, payload.name)

@srv.router.get("/stop")
def stop_service(request: Request, uid: str, _ = Depends(get_app)):
  micro.stop_service(uid)

  return srv.ok()

class ServiceInputModel(BaseModel):
  uid: str
  data: str

@srv.router.post("/send")
async def send_service_input(request: Request, uid: str, payload: ServiceInputModel, _ = Depends(get_app)):
  await micro.get_service(payload.uid).send(payload.data)

  return srv.ok()

@srv.router.get("/output")
def get_service_output(request: Request, uid: str, _ = Depends(get_app)):
  return micro.get_service(uid).get_output()

@srv.router.get("/stop-all")
def stop_all_service(request: Request, app = Depends(get_app)):
  micro.stop_services(app.name, True)

  return srv.ok()
