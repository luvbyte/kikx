import os
import sys
import pwd
import signal
import asyncio
import logging

from fastapi import Depends, Query, Request
from pydantic import BaseModel

from lib.os import get_username
from lib.service import create_service
from lib.utils import generate_uuid, joinpath, get_timestamp

from core.models.services import MicroConfigModel


logger = logging.getLogger(__name__)

srv = create_service(__file__, "Micro services for apps")


# ---------------------- Models
class ServiceInputModel(BaseModel):
  name: str
  data: str


# ---------------------- Utils
def get_app(request: Request):
  _, app = srv.get_client_app(request)

  if not app.config.has_service("micro"):
    srv.exception(403, "Service 'micro' not found in config")

  return app


# ---------------------- Micro Service
class Micro:
  def __init__(
    self,
    name: str,
    config: MicroConfigModel,
    app,
  ) -> None:
    self.name = name
    self.config = config
    self.created_at = get_timestamp()

    self.script_path = joinpath(
      app.get_app_path() / "micro",
      self.name,
      self.config.main,
    )

    if not self.script_path.is_file():
      raise FileNotFoundError("main file not found")

    self.app_id = app.id
    self.app_name = app.name
    self.app_title = app.title
    self.app_icon = app.manifest.icon
    self.sudo = app.is_sudo

    self.output: list[str] = []
    self.error_text: str | None = None
    self.started = False
    self.completed = False

    self.task: asyncio.Task | None = None
    self.started_event = asyncio.Event()

    self.env: dict[str, str] = os.environ.copy()

    self.cmd: list[str] = [
      sys.executable,
      *([] if self.config.stdout else ["-u"]),
      str(self.script_path),
    ]

    self.cwd = str(app.get_app_data_path())

    self.env.update({
      "KIKX_APP_ID": app.id,
      "KIKX_APP_NAME": app.name,
      "KIKX_STORAGE_PATH": str(app.user.storage_path),
      "KIKX_APP_PATH": str(app.get_app_path()),
      "KIKX_APP_DATA_PATH": str(app.get_app_data_path()),
      "KIKX_APP_CACHE_PATH": str(app.get_app_cache_path()),
      "KIKX_HOME_PATH": str(app.get_home_path()),
    })

    self.process: asyncio.subprocess.Process | None = None
    self.sid: int | None = None
    self.pgid: int | None = None

  def info(self) -> dict:
    return {
      "name": self.name,
      "app": {
        "id": self.app_id,
        "name": self.app_name,
        "title": self.app_title,
        "icon": self.app_icon,
        "sudo": self.sudo
      },
      "status": {
        "started": self.started,
        "running": self.is_running,
        "completed": self.completed,
      },
      "process": {
        "cmd": self.cmd,
        "cwd": self.cwd,
        "returncode": self.returncode,
        "error": self.error_text,
      },
      "config": self.config,
      "created_at": self.created_at
    }

  @property
  def returncode(self) -> int | None:
    return None if self.process is None else self.process.returncode

  @property
  def is_running(self) -> bool:
    return (
      self.process is not None
      and self.process.returncode is None
      and self.pgid is not None
    )

  @property
  def is_persistent(self) -> bool:
    return self.config.persistent

  def get_user(self) -> str:
    # Use the original user when running through sudo.
    username = os.environ.get("SUDO_USER", get_username())

    if username == "root":
      return "root" if self.sudo else "nobody"

    return username

  # ---------------------- output
  def on_output(self, data):
    self.output.append(data)

  # ---------------------- Process
  def demote(self, user_name: str):
    def result():
      pw = pwd.getpwnam(user_name)

      # Some sandboxed environments (Android's per-app SELinux policy under
      # Termux, in particular) deny setuid/setgid outright even when the
      # target identity is the one already running -- a pure no-op
      # everywhere else. Skip the call when nothing would actually change,
      # rather than failing a privilege change that was never needed.
      if pw.pw_uid == os.getuid() and pw.pw_gid == os.getgid():
        return

      os.setgid(pw.pw_gid)
      os.setuid(pw.pw_uid)

    return result

  def _create_process(self) -> asyncio.subprocess.Process:
    return asyncio.create_subprocess_exec(
      *self.cmd,
      env=self.env,
      stdout=asyncio.subprocess.PIPE if self.config.stdout else asyncio.subprocess.DEVNULL,
      stdin=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
      cwd=self.cwd,
      start_new_session=True,
      preexec_fn=self.demote(self.get_user()),
      limit=10 * 1024 * 1024,  # 10 MB
    )

  async def wait_for_complete(self) -> None:
    if self.config.stdout and self.process.stdout:
      while True:
        try:
          stdout_line = await asyncio.wait_for(
            self.process.stdout.readline(),
            timeout=30,
          )

          if not stdout_line:
            break
          
          self.on_output(stdout_line.decode())

        except asyncio.TimeoutError:
          if self.process.returncode is not None:
            break

    await self.process.wait()

    if self.process.stderr:
      stderr = await self.process.stderr.read()

      if stderr:
        self.error_text = stderr.decode()

  # ---------------------- Run
  async def run(self) -> None:
    try:
      self.process = await self._create_process()

      self.started = True
      self.sid = os.getsid(self.process.pid)
      self.pgid = os.getpgid(self.process.pid)

      self.started_event.set()

      await self.wait_for_complete()

    except Exception as e:
      self.error_text = str(e)
      logger.exception("Micro service '%s' failed", self.name)
      self.started_event.set()

    finally:
      self.completed = True

  # ---------------------- Output
  def get_output(self) -> list[str]:
    return self.output

  # ---------------------- Input
  async def send(self, data: str) -> None:
    if not self.is_running or self.process.stdin is None:
      raise RuntimeError("Micro Service not running")

    self.process.stdin.write(data.encode() + b"\n")
    await self.process.stdin.drain()

  # ---------------------- Kill
  async def _force_kill(self) -> None:
    if not self.is_running:
      logger.info(
        "Micro service '%s' already finished or not fully started",
        self.name,
      )
      return

    try:
      os.killpg(self.pgid, signal.SIGKILL)
      logger.info("Micro service '%s' force killed", self.name)
    except ProcessLookupError:
      pass

  async def _kill(self, wait: int = 3) -> None:
    if not self.is_running:
      logger.info(
        "Micro service '%s' already finished or not fully started",
        self.name,
      )
      return

    try:
      os.killpg(self.pgid, signal.SIGTERM)
    except ProcessLookupError:
      return

    try:
      await asyncio.wait_for(self.process.wait(), timeout=wait)
      logger.info(
        "Micro service '%s' gracefully stopped",
        self.name,
      )
    except asyncio.TimeoutError:
      await self._force_kill()

  # ---------------------- Clean
  async def clean(self) -> None:
    await self._kill()


# ---------------------- Service Manager
class MicroServices:
  def __init__(self) -> None:
    self._active: dict[str, dict[str, Micro]] = {}

  def get_active_services(self) -> dict[str, dict]:
    return {
      app_name: [
        service.info() for service in services.values()
      ]
      for app_name, services in self._active.items()
    }

  def get_app_active_services(self, app_name: str) -> dict[str, dict]:
    app_services = self._active.get(app_name, {})

    return {
      name: service.info()
      for name, service in app_services.items()
    }

  def get_service(
    self,
    app_name: str,
    name: str,
  ) -> Micro | None:
    return self._active.get(app_name, {}).get(name)

  # ---------------------- Start
  async def start_service(self, app, name: str) -> dict:
    app_services = self._active.setdefault(app.name, {})

    # Return the existing service if already active.
    service = app_services.get(name)

    if service is not None:
      return service.info()

    micro_config = app.config.get_service_config("micro")
    config = micro_config.get(name) if micro_config else MicroConfigModel()

    service = Micro(name, config, app)
    app_services[name] = service

    service.task = asyncio.create_task(service.run())

    await service.started_event.wait()

    return service.info()

  # ---------------------- Stop
  async def stop_service(self, app_name: str, name: str) -> None:
    services = self._active.get(app_name, {})
    service = services.get(name)

    if service is None:
      raise RuntimeError(
        f"Service {name} is not running; cannot stop it."
      )

    await service.clean()
    del services[name]

    if not services:
      del self._active[app_name]

  # ---------------------- Stop All
  async def stop_all(self, app_name: str) -> None:
    services = self._active.get(app_name)

    if not services:
      return

    for name, service in list(services.items()):
      await service.clean()
      del services[name]

    del self._active[app_name]

  # ---------------------- App Close
  async def remove_app_services(
    self, app_name: str,
    force: bool = False
  ):
    core = srv.get_core()

    # Other instances of this app are still active.
    if core.get_apps_by_name(app_name) and not force:
      return

    services = self._active.get(app_name)

    if not services:
      return

    # Keep persistent services unless forced.
    for name, service in list(services.items()):
      if service.is_persistent and not force:
        continue

      await service.clean()
      del services[name]

    if not services:
      del self._active[app_name]

  async def on_close_app(self, _, app_name: str) -> None:
    await self.remove_app_services(app_name)

  # ---------------------- Shutdown
  async def on_close(self) -> None:
    services = [
      service
      for app_services in self._active.values()
      for service in app_services.values()
    ]

    await asyncio.gather(
      *(service.clean() for service in services),
      return_exceptions=True,
    )

    self._active.clear()


micro = MicroServices()


# ---------------------- Lifecycle
@srv.on("startup")
def startup(core) -> None:
  core.events.add_event("app:close", micro.on_close_app)


@srv.on("shutdown")
async def shutdown(_) -> None:
  await micro.on_close()


# ---------------------- Routes
@srv.router.get("/list")
def list_app_active_services(
  request: Request,
  app=Depends(get_app),
):
  try:
    return micro.get_app_active_services(app.name)
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/start")
async def start_service(
  name: str = Query(...),
  app=Depends(get_app),
):
  try:
    return await micro.start_service(app, name)
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/stop")
async def stop_service(
  request: Request,
  name: str,
  app=Depends(get_app),
):
  try:
    await micro.stop_service(app.name, name)
    return srv.ok()
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/stop-all")
async def stop_all_service(
  request: Request,
  app=Depends(get_app),
):
  try:
    await micro.stop_all(app.name)
    return srv.ok()
  except Exception as e:
    srv.exception(500, e)


@srv.router.get("/output")
def get_service_output(
  request: Request,
  name: str,
  app=Depends(get_app),
):
  service = micro.get_service(app.name, name)

  if service is None:
    srv.exception(404, "Service not found")

  return service.get_output()


@srv.router.post("/send")
async def send_service_input(
  request: Request,
  payload: ServiceInputModel,
  app=Depends(get_app),
):
  service = micro.get_service(app.name, payload.name)

  if service is None:
    srv.exception(404, "Service not found")

  try:
    await service.send(payload.data)
    return srv.ok()
  except Exception as e:
    srv.exception(500, e)

# ---------------------- Micor Manager Routes
@srv.router.get("/manager/list")
def manager_list_services(request: Request):
  srv.get_client(request)

  return micro.get_active_services()

@srv.router.get("/manager/remove-app-services")
async def remove_app_services(
  request: Request,
  app_name: str,
  service_name: str | None = None
):
  srv.get_client(request)

  if service_name is None:
    await micro.remove_app_services(app_name, force=True)
  else:
    await micro.stop_service(app_name, service_name)
  
  return srv.ok()