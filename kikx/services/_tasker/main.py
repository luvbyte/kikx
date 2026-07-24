# Under development
import os
import pwd
import signal
import asyncio
import getpass

from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect

from lib.event import Events
from lib.parser import parse_config
from lib.service import create_service
from lib.utils import joinpath, generate_uuid, ensure_dir, send_event, is_websocket_connected

from core.logging import Logger

from pydantic import BaseModel
from typing import List


logging = Logger("kikx_service_os", "kikx_service_os.log")
logger = logging.get_logger()


srv = create_service(__file__)

def check_permisson(request: Request):
  core = srv.get_core()

  client, app = srv.get_client_or_app(request)
  if app is None: # allow access for clients
    return core

  # If app - check tasker exists in app config
  if not app.config.tasker:
    raise HTTPException(403, "Permission denied")

  return core

class TaskManifestModel(BaseModel):
  title: str
  # If string runs as shell / non-shell
  command: List[str] | str
  # autostart when kikx start
  autostart: bool = False

class TaskHandler:
  def __init__(self):
    self.data: list[str] = []
    self.errors: list[str] = []

    self.websockets: list[WebSocket] = []

  def connect(self, ws):
    self.websockets.append(ws)

  def disconnect(self, ws):
    self.websockets.remove(ws)
  
  async def broadcast(self, event, payload = None):
    if not self.websockets:
      return

    # Fire off all sends concurrently
    tasks = [send_event(ws, event, payload) for ws in self.websockets]
    await asyncio.gather(*tasks, return_exceptions=True)
  
  # ------------ EVENTS
  async def on_create(self, task):
    await self.broadcast("create")

  async def on_start(self, task):
    await self.broadcast("start")

  async def on_kill(self, task):
    await self.broadcast("kill")

  async def on_end(self, task):
    await self.broadcast("end")

  async def on_data(self, task, data):
    self.data.append(data)
    await self.broadcast("output", data)

  async def on_error(self, task, error):
    self.errors.append(error)
    await self.broadcast("error", error)

# Task Base
class Task:
  def __init__(self, name, task_path, ttype: str):
    self.events = Events()
    self.task_handler = TaskHandler()
  
    self.name = name
    self.ttype = ttype
    self.id = generate_uuid()
    self.manifest = self.load_manifest(task_path)
    
    self._cwd = None
    self.stdout_timeout = 30

    self.stdin = asyncio.subprocess.PIPE
    self.stdout = asyncio.subprocess.PIPE
    self.stderr = asyncio.subprocess.PIPE

    self.ended = False
    self.process = None
    self.running = False
    self._cleaned = False

    # Task events
    self.events.add_event("create", self.task_handler.on_create)
    self.events.add_event("start", self.task_handler.on_start)
    self.events.add_event("kill", self.task_handler.on_kill)
    self.events.add_event("end", self.task_handler.on_end)
    self.events.add_event("data", self.task_handler.on_data)
    self.events.add_event("error", self.task_handler.on_error)

  def load_manifest(self, path):
    return parse_config(path, TaskManifestModel)
  
  @property
  def is_shell(self):
    return isinstance(self.manifest.command, str)
  
  @property
  def cwd(self) -> str:
    if self._cwd is None:
      raise Exception("Task cwd is none")
    
    return str(self._cwd)

  def get_user(self) -> str:
    return getpass.getuser()

  def demote(self, user_name):
    def result():
      pw = pwd.getpwnam(user_name)
      os.setgid(pw.pw_gid)
      os.setuid(pw.pw_uid)
    return result

  async def run(self):
    if self.running:
      raise Exception("Task already running")
    # ------------ Code
    user = self.get_user()
    preexec = None if user == "root" else self.demote(user)

    if self.is_shell:
      self.process = await asyncio.create_subprocess_shell(
        self.manifest.command,
        stdout=self.stdout,
        stdin=self.stdin,
        stderr=self.stderr,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec,
        limit=10 * 1024 * 1024 # 10 mb
      )
    else:
      self.process = await asyncio.create_subprocess_exec(
        *self.manifest.command,
        stdout=self.stdout,
        stdin=self.stdin,
        stderr=self.stderr,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec,
        limit=10 * 1024 * 1024 # 10 mb
      )

    # STATE & EVENT
    self.running = True
    await self.events.emit("start", self)

    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)
    logger.info(f"Tasker started ({self.ttype}): {self.id} with command: {self.manifest.command}")
    
    while True:
      try:
        stdout_line = await asyncio.wait_for(self.process.stdout.readline(), timeout=self.stdout_timeout)
        if not stdout_line:
          break
        await self.events.emit("data", self, stdout_line.decode())
      except asyncio.TimeoutError:
        if self.process.returncode is not None:
          break

    await self.process.wait()
    stderr = await self.process.stderr.read()
    if stderr:
      await self.events.emit("error", self, stderr.decode())

    # ------------ End
    self.ended = True
    self.running = False

    await self.events.emit("end", self)

    return self.id

  async def send(self, data: str) -> None:
    if not self.process or self.process.returncode is not None:
      raise Exception("No active process")

    self.process.stdin.write(data.encode() + b'\n')
    await self.process.stdin.drain()

  async def _force_kill(self):
    if not self.process or self.process.returncode is not None:
      logger.info(f"Task {self.id} already finished")
      return

    try:
      os.killpg(self.pgid, signal.SIGKILL)
      await self.events.emit("kill", self)
      logger.warning(f"Task {self.id} (SID {self.sid}) forcefully killed")
    except Exception as e:
      logger.error(f"Force kill failed for {self.id}: {e}")

  async def clean(self) -> None:
    if self._cleaned:
      return
    await self._force_kill()
    self._cleaned = True

# App Task
class AppTask(Task):
  def __init__(self, name, task_path, app_id, app_name):
    super().__init__(name, task_path, "app")

    self.app_id: str = app_id
    self.app_name: str = app_name

# Client Task
class ClientTask(Task):
  def __init__(self, name, task_path, client_id):
    super().__init__(name, task_path, "client")

    self.client_id: str = client_id

class Config:
  def __init__(self):
    pass

  def get_client_task_path(self, core, client, name):
    return joinpath(core.config.uis_path / client.ui.name / "tasker", f"{name}.json")

  def get_app_task_path(self, core, app, name):
    return joinpath(core.config.apps_path / app.name / "tasker", f"{name}.json")
  
  def get_task_data_path(self, core, task_id):
    return ensure_dir(core.config.data_path / "tasker" / task_id)

# Tasker Core
class Tasker:
  def __init__(self):
    self.config = Config()
    self._tasks: dict[str, Task] = {}
    self._qtasks = [] # Temp tasks

  def get_task(self, task_id: str):
    return self._tasks[task_id]
  
  # ------------ TASK EVENT CALLBACKS
  # On task run completed
  def __coro_complete(self, task_id: str):
    print(f"Tasker complete: {task_id}")
  
  async def on_task_create(self, task: Task):
    print(f"Tasker created: {task.name}")
  
  async def on_task_start(self, task: Task):
    print(f"Tasker started: {task.name}")

  async def on_task_data(self, task: Task, data):
    print(f"Tasker: {task.name}, Data: {data}")

  async def on_task_error(self, task: Task, data):
    print(f"Tasker Error: {task.name}, Data: {data}")

  async def on_task_kill(self, task: Task):
    print(f"Tasker kill: {task.name}")

  async def on_task_end(self, task: Task):
    print(f"Tasker ended: {task.id} {task.name}")
  
  # ------------ TASK EVENT BINDS
  def add_task_events(self, task):
    task.events.add_event("create", self.on_task_create)
    task.events.add_event("start", self.on_task_start)
    task.events.add_event("data", self.on_task_data)
    task.events.add_event("error", self.on_task_error)
    task.events.add_event("kill", self.on_task_kill)
    task.events.add_event("end", self.on_task_end)

  # ------------ TASK
  async def start_task(self, task: Task):
    t = asyncio.create_task(task.run(), name=task.id)
    t.add_done_callback(self.__coro_complete)
  
  async def create_client_task(self, core, client, payload):
    # get client ui and path
    task_path = self.config.get_client_task_path(core, client, payload.name)
    task = ClientTask(payload.name, task_path, client.id)
    task._cwd = self.config.get_task_data_path(core, task.id)
    self._tasks[task.id] = task

    self.add_task_events(task)

    await task.events.emit("create", task)

    if payload.autostart:
      await self.start_task(task)
  
    return { "taskID": task.id }

  async def create_app_task(self, core, app, payload):
    task_path = self.config.get_app_task_path(core, app, payload.name)
    task = AppTask(payload.name, task_path, app.id)
    
    task._cwd = self.config.get_task_data_path(core, task.id)
    self._tasks[task.id] = task

    self.add_task_events(task)
    
    await task.events.emit("create", task)

    if payload.autostart:
      await self.start_task(task)

    return { "taskID": task.id }
  
  async def send_app_task_input(self, core, app, task_id: str, data: str):
    task = self.get_task(task_id)
    
    await task.send(data)

  async def send_clien_task_input(self, core, client, task_id: str, data: str):
    task = self.get_task(task_id)

    await task.send(data)

  async def kill_app_task(self, core, app, task_id: str):
    task = self.get_task(task_id)

    await task.clean()

  async def kill_client_task(self, core, client, task_id: str):
    task = self.get_task(task_id)

    await task.clean()

  # ------------ LIST TASKS
  def list_client_tasks(self):
    pass

  def list_app_tasks(self):
    pass
  
  async def on_shutdown(self) -> None:
    logger.info("Shutting down all tasker running tasks")

    # Cancel all asyncio tasks
    tasks = [t.clean() for t in self._tasks.values()]
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("All tasks closed cleanly for tasker service")


tasker = Tasker()


@srv.on("shutdown")
async def on_shutdown(core):
  await tasker.on_shutdown()

class CreateTaskModel(BaseModel):
  name: str
  autostart: bool = False

class TaskInputModel(BaseModel):
  task_id: str
  data: str

@srv.router.post("/create")
async def create_task(payload: CreateTaskModel, request: Request, core = Depends(check_permisson)):
  client, app = srv.get_client_or_app(request)

  if app: # App task
    return await tasker.create_app_task(core, app, payload)
  else:  # Client task
    return await tasker.create_client_task(core, client, payload)

@srv.router.get("/start")
async def start_task(task_id: str, request: Request, core = Depends(check_permisson)):
  client, app = srv.get_client_or_app(request)

  task = tasker.get_task(task_id)
  return await tasker.start_task(task)

@srv.router.post("/send")
async def send_task_input(payload: TaskInputModel, request: Request, core = Depends(check_permisson)):
  client, app = srv.get_client_or_app(request)

  if app: # App task
    return await tasker.send_app_task_input(core, app, payload.task_id, payload.data)
  else:  # Client task
    return await tasker.send_clien_task_input(core, client, payload.task_id, payload.data)

@srv.router.get("/kill")
async def kill_task(task_id: str, request: Request, core = Depends(check_permisson)):
  client, app = srv.get_client_or_app(request)

  if app: # App task
    return await tasker.kill_app_task(core, app, task_id)
  else:  # Client task
    return await tasker.kill_clien_task(core, client, task_id)

@srv.router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
  await websocket.accept()
  
  task = tasker.get_task(task_id)
  task.task_handler.connect(websocket)
  
  logger.info(f"WS Attach for task: {task.id}")

  while True:
    try:
      text = await websocket.receive_text()
      await task.send(text)
    except WebSocketDisconnect:
      task.task_handler.disconnect(websocket)
      break
    except Exception as e:
      print("Tasker ws exception:", e)
