import os
import sys
import pwd
import json
import shlex
import signal
import asyncio
import logging

from uuid import uuid4
from pathlib import Path
from typing import Any, Callable
from pydantic import BaseModel, Field

from core.func import funcx
from core.func.handlers import Handler
from core.models.app_models import AppModuleTasksConfigModel

from lib.storage import KVStorage



# Logger
logger = logging.getLogger(__name__)



class TaskKVStorage(KVStorage):
  async def func(self, name, options):
    if name not in ["set", "pop", "reset"]:
      raise Exception("Invalid func name")


class SafeDict(dict):
  def __missing__(self, key: str) -> str:
    return '{' + key + '}'


class QTask:
  def __init__(self, cmd: str, env: dict[str, str], shell: bool, cwd: str, sudo: bool) -> None:
    # Task ID
    self.id: str = uuid4().hex
    # Task working directory
    self.cwd: str = cwd
    # Sudo task
    self.sudo: bool = sudo
    # Subprocess Shell
    self.shell: bool = shell
    # Run Command
    self.cmd: str = cmd 
    # Task env
    self.env: dict[str, str] = env
    # Task process
    self.process: asyncio.subprocess.Process | None = None
    self.sid: int | None = None
    self.pgid: int | None = None

    # Task stdio
    self.stdout = asyncio.subprocess.PIPE
    self.stdin = asyncio.subprocess.PIPE
    self.stderr = asyncio.subprocess.PIPE
    
    # Task states
    self._cleaned = False

  @property
  def returncode(self) -> int | None:
    return None if self.process is None else self.process.returncode
  
  # Get user for task
  def get_user(self) -> str:
    return "root" if self.sudo else "nobody"
  
  # Demote user
  def demote(self, user_name: str) -> Callable:
    def result():
      pw = pwd.getpwnam(user_name)
      os.setgid(pw.pw_gid)
      os.setuid(pw.pw_uid)
    return result

  # Create Process
  def _create_process(self) -> asyncio.subprocess.Process:
    if self.sudo:
      preexec = None  # stay root
    else:
      preexec = self.demote(self.get_user())

    if self.shell:
      return asyncio.create_subprocess_shell(
        self.cmd,
        env=self.env,
        stdout=self.stdout,
        stdin=self.stdin,
        stderr=self.stderr,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec,
        limit=10 * 1024 * 1024 # 10 mb
      )
    else:
      return asyncio.create_subprocess_exec(
        *shlex.split(self.cmd),
        env=self.env,
        stdout=self.stdout,
        stdin=self.stdin,
        stderr=self.stderr,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec,
        limit=10 * 1024 * 1024 # 10 mb
      )
  
  # Run quick Task
  async def run(self, input_text: str) -> dict:
    self.process = await self._create_process()

    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)

    stdout, stderr = await self.process.communicate(
      input_text.encode() if input_text is not None else None
    )

    return {
      "returncode": self.process.returncode,
      "stdout": stdout,
      "stderr": stderr,
    }
    
  # Force kill task with sigint fastest
  async def _force_kill(self) -> None:
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

  # Kill task and clean
  async def clean(self) -> None:
    if self._cleaned:
      return
    await self._force_kill()
    self._cleaned = True
  

class Task(QTask):
  def __init__(self, cmd: str, env: dict[str, str], shell: bool, cwd: str, sudo: bool, allow_commands: bool, output_mode: str) -> None:
    super().__init__(cmd, env, shell, cwd, sudo)
    
    # Task States
    self.started: bool = False
    self.completed: bool = False

    # Stdout waiting timeout
    self.stdout_timeout: int = 3
    
    # Allow task commands
    self.allow_commands: bool = allow_commands

    # Save output
    self._output_mode: str = output_mode # send | save | *
    # Task output storing
    self.task_output: dict[str, dict] = {}

    # Error text
    self.error_text: str | None = None

    # Output message index
    self.output_index: int = 0

  @property
  def is_output_both(self) -> bool:
    return self._output_mode == "*"

  @property
  def is_output_save(self) -> bool:
    return self._output_mode == "save" or self.is_output_both

  @property
  def is_output_send(self) -> bool:
    return self._output_mode == "send" or self.is_output_both

  # Get task info
  def info(self) -> dict:
    return {
      "id": self.id,
      "is_shell": self.shell,
      "started": self.started,
      "completed": self.completed,
      "error_text": self.error_text,
      "output_index": self.output_index,
      "output_count": len(self.task_output),
      "output_mode": self._output_mode,
      "allow_commands": self.allow_commands,
      "stdout_timeout": self.stdout_timeout,
      "sudo": self.sudo,
      "cleaned": self._cleaned,
      "returncode": self.returncode
    }

  # Get task output list
  def get_task_output(self, index: int | None = None) -> list:
    if index is None:
      return list(self.task_output.values())

    return [self.task_output.get(f"i_{index}", None)]

  # Clear task output
  def clear_output(self) -> None:
    self.task_output.empty()

  # Send Input to process
  async def send(self, data: str) -> None:
    if not self.process or self.process.returncode is not None:
      raise Exception("No active process")

    self.process.stdin.write(data.encode() + b'\n')
    await self.process.stdin.drain()
  
  # Task command : !_KIKX_!{ 'event': 'something', 'payload': {} } (development)
  async def _on_command(self, event: str, payload: dict) -> Any:
    if event == "kv":
      return await self.kv_storage.func(payload["name"], payload["options"])
  
  # On task command
  async def on_command(self, command) -> Any:
    try:
      event, payload = json.loads(command).values()
      if not isinstance(event, str):
        raise Exception("Task command event must be string")

      return await self._on_command(event, payload)
    except Exception as e:
      logger.info(f"Task ({self.id}) command Exception:", e)
  
  # On task output
  async def on_output(self, handler: Handler, decoded_line: str) -> None:
    data = {
      "index": self.output_index,
      "message": decoded_line
    }

    if self.is_output_send and handler:
      await handler.output(data)
    if self.is_output_save:
      self.task_output[f"i_{self.output_index}"] = data

    self.output_index += 1
  
  # Run
  async def run(self, handler: Handler | None) -> str:
    if self.started or self.process:
      handler and await handler.error("Can't re-run task, Its already running")
      raise Exception("Can't re-run task, Its already running")

    self.completed = False
    
    self.process = await self._create_process()
    
    self.started = True
    self._cleaned = False
    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)

    logger.info(f"Task started: {self.id} with command: {self.cmd}")
    
    while True:
      try:
        stdout_line = await asyncio.wait_for(self.process.stdout.readline(), timeout=self.stdout_timeout)
        if not stdout_line:
          break
        
        decoded_line = stdout_line.decode()
        decoded_line_strip = decoded_line.strip()
        
        # If task command
        if self.allow_commands and decoded_line_strip[:8] == "!_KIKX_!":
          await self.on_command(decoded_line_strip[8:])
          continue
        
        await self.on_output(handler, decoded_line)
      except asyncio.TimeoutError:
        handler and await handler.info(f"Task {self.id}: No output for {self.stdout_timeout} seconds, checking process...\n")
        if self.process.returncode is not None:
          break

    await self.process.wait()

    stderr = await self.process.stderr.read()
    if stderr:
      self.error_text = stderr.decode()
      handler and await handler.error(self.error_text)

    self.completed = True

    return self.id


class Tasks:
  def __init__(self, app, config: dict) -> None:
    # tasks config {}
    self.app_id: str = app.id
    self.app_name: str = app.name
    self.config: AppModuleTasksConfigModel = AppModuleTasksConfigModel(**config)
    self.app_path: Path = app.app_path

    self.kv_storage: TaskKVStorage = TaskKVStorage()
    self.task_cwd: str = str(app.get_app_data_path())

    # If not sandbox then copies program env
    self.task_env: dict[str, str] = {} if self.config.sandbox else os.environ.copy()

    # Include kikx_env variables must shell True
    if self.config.kikx_env and self.config.shell:
      self.task_env.update({
        "KIKX_APP_ID": app.id,
        "KIKX_APP_NAME": app.name,
        "KIKX_STORAGE_PATH": str(app.user.storage_path),
        "KIKX_APP_PATH": str(app.get_app_path()),
        "KIKX_APP_DATA_PATH": str(app.get_app_data_path()),
        "KIKX_HOME_PATH": str(app.get_home_path())
      })

    # Format paths for task template
    # Task template
    self.task_template: str = self.config.main.format_map(SafeDict({
      "app_name": app.name,
      "app_path": str(app.get_app_path()),
      "storage_path": str(app.user.storage_path),
      "data_path": str(app.get_app_data_path()),
      "home_path": str(app.get_home_path())
    }))

    # Updating env with user env values
    self.task_env.update(self.config.env)

    # Program paths
    self.task_env.update({
      # 1. app/bin | 2. storage/bin | 3. kikx path
      "PATH": f'{str(self.app_path / "bin")}:{app.user.get_path_env()}:{str(Path(sys.executable).parent)}:{self.task_env.get("PATH", "")}'
    })

    # If app run as Sudo
    self.sudo: bool = app.is_sudo #
    
    # Send app message event
    self.send_event = app.send_event
    
    self.active_tasks: dict[str, Task] = {}
    
    # coro tasks
    self.coro_tasks: list[asyncio.Task] = []

  def __on_coro_task_complete(self, task: asyncio.Task) -> None:
    if task in self.coro_tasks:
      logger.info(f"CoroTask completed: {task.get_name()}")
      self.coro_tasks.remove(task)

  def get_task(self, task_id: str) -> Task:
    task = self.active_tasks.get(task_id)
    if not task:
      raise Exception(f"Task not found: {task_id}")

    return task

  async def _run_task(self, task: Task, handler: Handler | None) -> None:
    """Run and monitor the task."""
    try:
      handler and await handler.started("Task started\n")
      return await task.run(handler)
    except Exception as e:
      logger.exception(f"Error while running task {task.id}")
      handler and await handler.error(str(e))
    except asyncio.CancelledError:
      logger.info(f"CoroTask cancelled: {task.id}")
    finally:
      await task.clean()

      handler and await handler.ended("CoroTask ended\n")

  # --------- Create task
  @funcx
  async def create_task(
    self,
    task_cmd: str,
    no_sudo: bool = False,
    allow_commands: bool = False,
    output_mode: str = "send"
  ) -> dict:
    split_cmd = shlex.split(task_cmd)
    if len(split_cmd) <= 0:
      raise Exception("Command not found")
    
    cmd_name = split_cmd[0]
    cmd_args = " ".join(split_cmd[1:])

    task_cmd = self.task_template.format_map(SafeDict({
      "name": cmd_name,
      "args": cmd_args
    }))

    # No sudo or sudo from app
    sudo = False if no_sudo else self.sudo

    task = Task(task_cmd, self.task_env, self.config.shell, self.task_cwd, sudo, allow_commands, output_mode)

    self.active_tasks[task.id] = task

    return task.info()

  # --------- Run task
  @funcx
  async def run_task(self, task_id: str, handler_id: str | None) -> dict:
    task = self.get_task(task_id)
    
    handler = Handler(handler_id, self.send_event) if handler_id else None

    coro_task = asyncio.create_task(self._run_task(task, handler), name=task.id)
    coro_task.add_done_callback(self.__on_coro_task_complete)
    self.coro_tasks.append(coro_task)

    return task.info()

  # --------- Quick run task
  @funcx
  async def quick_run(self, task_cmd: str, no_sudo: bool = False, input_args: list[str] | None = None) -> dict:
    split_cmd = shlex.split(task_cmd)
    if len(split_cmd) <= 0:
      raise Exception("Command not found")
    
    cmd_name = split_cmd[0]
    cmd_args = " ".join(split_cmd[1:])

    task_cmd = self.task_template.format_map(SafeDict({
      "name": cmd_name,
      "args": cmd_args
    }))
    
    task_input = "\n".join(input_args or [])

    # No sudo or sudo from app
    sudo = False if no_sudo else self.sudo

    task = QTask(task_cmd, self.task_env, self.config.shell, self.task_cwd, sudo)

    self.active_tasks[task.id] = task

    try:
      return await task.run(task_input)
    except asyncio.CancelledError:
      raise Exception("Task cancelled")
    finally:
      await task.clean()

  # --------- Kill task / remove from tasks
  @funcx
  async def kill(self, task_id: str, remove: bool = False) -> None:
    """Cancel a running task."""
    coro_task = next((t for t in self.coro_tasks if t.get_name() == task_id), None)
    if coro_task:
      coro_task.cancel()
      logger.info(f"Task killed ID: {task_id}")
    
    # Remove task 
    if remove:
      logger.info(f"Task removing: {task_id}")
      self.active_tasks.pop(task_id, None)

  # --------- Send input to task
  @funcx
  async def send_input(self, task_id: str, input_text: str) -> None:
    """Send input to a running task."""
    return await self.get_task(task_id).send(input_text)
  
  # --------- Get task info
  @funcx
  async def get_task_info(self, task_id: str) -> dict:
    """Get task info"""
    return self.get_task(task_id).info()

  # --------- Get task output list
  @funcx
  async def get_task_output(self, task_id: str, *args, **options) -> list:
    """Get task output"""
    return self.get_task(task_id).get_task_output(*args, **options)

  # --------- Run task command
  @funcx
  async def task_command(self, task_id: str, event: str, payload: Any) -> Any:
    """Run task command"""
    return await self.get_task(task_id)._on_command(event, payload)

  # --------- Clear task output list
  @funcx
  async def clear_task_ouput(self, task_id: str) -> None:
    self.get_task(task_id).clear_output()

  # -------------------------------
  async def on_close(self) -> None:
    """Cancel and clean all background tasks safely."""
    logger.info(f"Closing App Tasks: {self.app_name} (ID: {self.app_id})")

    if not self.coro_tasks and not self.active_tasks:
      return

    logger.info(f"Shutting down all running tasks for (App: {self.app_name}) (ID: {self.app_id})...")

    # Cancel all asyncio tasks
    for t in list(self.coro_tasks):
      t.cancel()

    # Wait briefly for cooperative exit
    if self.coro_tasks:
      done, pending = await asyncio.wait(self.coro_tasks, timeout=1.5)
      for p in pending:
        logger.warning(f"Force-cancelling {p.get_name()}")
        p.cancel()

    # Ensure subprocesses are killed
    for task in list(self.active_tasks.values()):
      await task.clean()
    
    self.coro_tasks.clear()
    self.active_tasks.clear()

    logger.info(f"All tasks closed cleanly for (App: {self.app_name}) (ID: {self.app_id}).")

