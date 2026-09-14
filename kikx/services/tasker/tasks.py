import asyncio
import logging
import os
import pwd
import shlex
import signal
import sys

from pathlib import Path
from typing import Callable

from lib.os import get_username
from lib.utils import generate_uuid

from core.models.services import TaskerConfigModel

from .handler import Handler


logger = logging.getLogger(__name__)


# ---------------------- Safe Dict
class SafeDict(dict):
  def __missing__(self, key: str) -> str:
    return "{" + key + "}"


# ---------------------- Quick Task
class QTask:
  def __init__(
    self,
    cmd: str,
    env: dict[str, str],
    shell: bool,
    cwd: str,
    sudo: bool,
  ) -> None:
    self.id = generate_uuid()
    self.cwd = cwd
    self.sudo = sudo
    self.shell = shell
    self.cmd = cmd
    self.env = env

    self.process: asyncio.subprocess.Process | None = None
    self.sid: int | None = None
    self.pgid: int | None = None

    self.stdout = asyncio.subprocess.PIPE
    self.stdin = asyncio.subprocess.PIPE
    self.stderr = asyncio.subprocess.PIPE

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

  def get_user(self) -> str:
    # Use the original user when running through sudo.
    username = os.environ.get("SUDO_USER", get_username())

    if username == "root":
      return "root" if self.sudo else "nobody"

    return username

  # ---------------------- Process
  def demote(self, user_name: str) -> Callable:
    def result():
      pw = pwd.getpwnam(user_name)
      os.setgid(pw.pw_gid)
      os.setuid(pw.pw_uid)

    return result

  def _create_process(self) -> asyncio.subprocess.Process:
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
        limit=10 * 1024 * 1024,  # 10 MB
      )

    return asyncio.create_subprocess_exec(
      *shlex.split(self.cmd),
      env=self.env,
      stdout=self.stdout,
      stdin=self.stdin,
      stderr=self.stderr,
      cwd=self.cwd,
      start_new_session=True,
      preexec_fn=preexec,
      limit=10 * 1024 * 1024,  # 10 MB
    )

  # ---------------------- Run
  async def run(self, input_text: str | None) -> dict:
    self.process = await self._create_process()

    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)

    stdout, stderr = await self.process.communicate(
      input_text.encode() if input_text is not None else None,
    )

    return {
      "returncode": self.process.returncode,
      "stdout": stdout,
      "stderr": stderr,
    }

  # ---------------------- Kill
  async def _force_kill(self) -> None:
    if not self.is_running:
      logger.info(
        "Task '%s' already finished or not fully started",
        self.id,
      )
      return

    try:
      os.killpg(self.pgid, signal.SIGKILL)
      logger.info("Task force killed: %s", self.id)
    except ProcessLookupError:
      pass

  async def _kill(self, wait: int = 3) -> None:
    if not self.is_running:
      logger.info(
        "Task '%s' already finished or not fully started",
        self.id,
      )
      return

    try:
      os.killpg(self.pgid, signal.SIGTERM)
    except ProcessLookupError:
      return

    try:
      await asyncio.wait_for(
        self.process.wait(),
        timeout=wait,
      )

      logger.info(
        "Task gracefully killed: %s",
        self.id,
      )

    except asyncio.TimeoutError:
      await self._force_kill()

  async def clean(self) -> None:
    await self._kill()


# ---------------------- Task
class Task(QTask):
  def __init__(
    self,
    cmd: str,
    env: dict[str, str],
    shell: bool,
    cwd: str,
    sudo: bool,
    output_mode: str,
  ) -> None:
    super().__init__(
      cmd,
      env,
      shell,
      cwd,
      sudo,
    )

    self.started = False
    self.completed = False

    self.stdout_timeout = 3

    # send | save | *
    self._output_mode = output_mode

    self.task_output: dict[str, dict] = {}
    self.error_text: str | None = None
    self.output_index = 0

  @property
  def is_output_both(self) -> bool:
    return self._output_mode == "*"

  @property
  def is_output_save(self) -> bool:
    return self._output_mode in {"save", "*"}

  @property
  def is_output_send(self) -> bool:
    return self._output_mode in {"send", "*"}

  # ---------------------- Info
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
      "stdout_timeout": self.stdout_timeout,
      "sudo": self.sudo,
      "running": self.is_running,
      "returncode": self.returncode,
    }

  # ---------------------- Output
  def get_task_output(
    self,
    index: int | None = None,
  ) -> list:
    if index is None:
      return list(self.task_output.values())

    return [self.task_output.get(f"i_{index}")]

  def clear_output(self) -> None:
    self.task_output.clear()

  # ---------------------- Input
  async def send(self, data: str) -> None:
    if not self.is_running or self.process.stdin is None:
      raise RuntimeError("Task not running")

    self.process.stdin.write(
      str(data).encode() + b"\n",
    )

    await self.process.stdin.drain()

  # ---------------------- Output Handler
  async def on_output(
    self,
    handler: Handler | None,
    decoded_line: str,
  ) -> None:
    data = {
      "index": self.output_index,
      "message": decoded_line,
    }

    if self.is_output_send and handler is not None:
      await handler.output(data)

    if self.is_output_save:
      self.task_output[f"i_{self.output_index}"] = data

    self.output_index += 1

  # ---------------------- Run
  async def run(self, handler: Handler | None) -> str:
    if self.started or self.process is not None:
      if handler is not None:
        await handler.error(
          "Can't re-run task, Its already running",
        )

      raise RuntimeError(
        "Can't re-run task, Its already running",
      )

    self.completed = False
    self.process = await self._create_process()

    self.started = True
    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)

    logger.info(
      "Task started: %s | cmd=%s",
      self.id,
      self.cmd,
    )

    while True:
      try:
        stdout_line = await asyncio.wait_for(
          self.process.stdout.readline(),
          timeout=self.stdout_timeout,
        )

        if not stdout_line:
          break

        await self.on_output(
          handler,
          stdout_line.decode(),
        )

      except asyncio.TimeoutError:
        if handler is not None:
          await handler.info(
            f"Task {self.id}: No output for "
            f"{self.stdout_timeout} seconds, checking process...\n"
          )

        if self.process.returncode is not None:
          break

    await self.process.wait()

    stderr = await self.process.stderr.read()

    if stderr:
      self.error_text = stderr.decode()

      if handler is not None:
        await handler.error(self.error_text)

    self.completed = True

    return self.id


# ---------------------- Tasks
class Tasks:
  def __init__(self, app) -> None:
    self.app_id = app.id
    self.app_name = app.name
    self.app_path: Path = app.app_path

    # Use the tasker config or the default config.
    self.config: TaskerConfigModel = (
      app.config.get_service_config("tasker")
      or TaskerConfigModel()
    )

    self.task_cwd = str(app.get_app_data_path())

    # Sandboxed tasks start with an empty environment.
    self.task_env: dict[str, str] = (
      {}
      if self.config.sandbox
      else os.environ.copy()
    )

    if self.config.kikx_env:
      self.task_env.update({
        "KIKX_APP_ID": app.id,
        "KIKX_APP_NAME": app.name,
        "KIKX_STORAGE_PATH": str(app.user.storage_path),
        "KIKX_APP_PATH": str(app.get_app_path()),
        "KIKX_APP_DATA_PATH": str(app.get_app_data_path()),
        "KIKX_APP_CACHE_PATH": str(app.get_app_cache_path()),
        "KIKX_HOME_PATH": str(app.get_home_path()),
      })

    # Format the task command template.
    self.task_template = self.config.main.format_map(
      SafeDict({
        "app_name": app.name,
        "app": str(app.get_app_path()),
        "storage": str(app.user.storage_path),
        "data": str(app.get_app_data_path()),
        "cache": str(app.get_app_cache_path()),
        "home": str(app.get_home_path()),
      })
    )

    # Add configured environment variables.
    self.task_env.update(self.config.env)

    # Add app/bin, user paths and the Python executable path.
    self.task_env.update({
      "PATH": (
        f"{self.app_path / 'bin'}:"
        f"{app.user.get_path_env()}:"
        f"{Path(sys.executable).parent}:"
        f"{self.task_env.get('PATH', '')}"
      ),
    })

    self.sudo = app.is_sudo
    self.send_event = app.send_event

    self.active_tasks: dict[str, Task] = {}

  def __on_coro_task_complete(
    self,
    task: asyncio.Task,
  ) -> None:
    logger.info(
      "Task completed: %s",
      task.get_name(),
    )

  # ---------------------- Get Task
  def get_task(self, task_id: str) -> Task:
    task = self.active_tasks.get(task_id)

    if task is None:
      raise RuntimeError(f"Task not found: {task_id}")

    return task

  # ---------------------- Run Task
  async def _run_task(
    self,
    task: Task,
    handler: Handler | None,
  ) -> None:
    try:
      if handler is not None:
        await handler.started("Task started\n")

      await task.run(handler)

    except Exception as e:
      logger.exception(
        "Error while running task %s",
        task.id,
      )

      if handler is not None:
        await handler.error(str(e))

    finally:
      await task.clean()

      if handler is not None:
        await handler.ended("Task ended\n")

  def _parse_task_cmd(self, cmd: str) -> str:
    split_cmd = shlex.split(cmd)

    if not split_cmd:
      raise ValueError("Command not found")

    cmd_name = split_cmd[0]
    cmd_args = " ".join(split_cmd[1:])

    return self.task_template.format_map(
      SafeDict({
        "python": sys.executable,
        "name": cmd_name,
        "args": cmd_args,
      })
    )

  # ---------------------- Create Task
  async def create_task(
    self,
    cmd: str,
    can_sudo: bool = False,
    output_mode: str = "send",
  ) -> dict:
    task_cmd = self._parse_task_cmd(cmd)

    sudo = can_sudo and self.sudo

    task = Task(
      task_cmd,
      self.task_env,
      self.config.shell,
      self.task_cwd,
      sudo,
      output_mode,
    )

    self.active_tasks[task.id] = task

    return task.info()

  # ---------------------- Run Task
  async def run_task(
    self,
    task_id: str,
    handler_id: str | None,
  ) -> dict:
    task = self.get_task(task_id)

    if task.is_running:
      raise RuntimeError("Task already running")

    handler = (
      Handler(handler_id, self.send_event)
      if handler_id
      else None
    )

    coro_task = asyncio.create_task(
      self._run_task(task, handler),
      name=task.id,
    )

    coro_task.add_done_callback(
      self.__on_coro_task_complete,
    )

    return task.info()

  # ---------------------- Quick Run
  async def quick_run(
    self,
    cmd: str,
    can_sudo: bool = False,
    input_args: list[str] | None = None,
    timeout: float | None = None,
  ) -> dict:
    task_cmd = self._parse_task_cmd(cmd)
    task_input = "\n".join(input_args or [])

    sudo = can_sudo and self.sudo

    task = QTask(
      task_cmd,
      self.task_env,
      self.config.shell,
      self.task_cwd,
      sudo,
    )

    self.active_tasks[task.id] = task

    try:
      if timeout is not None:
        return await asyncio.wait_for(
          task.run(task_input),
          timeout=timeout,
        )

      return await task.run(task_input)

    except asyncio.TimeoutError:
      raise RuntimeError("Task timed out")

    finally:
      await task.clean()
      self.remove_task(task.id)

  # ---------------------- Remove
  def remove_task(self, task_id: str) -> None:
    if self.active_tasks.pop(task_id, None) is not None:
      logger.info(
        "Task removed: %s | app=%s | app_id=%s",
        task_id,
        self.app_name,
        self.app_id,
      )

  # ---------------------- Kill
  async def kill(
    self,
    task_id: str,
    remove: bool = False,
  ) -> None:
    task = self.get_task(task_id)

    await task.clean()

    if remove:
      self.remove_task(task_id)

  # ---------------------- Input
  async def send_input(
    self,
    task_id: str,
    input_text: str,
  ) -> None:
    await self.get_task(task_id).send(input_text)

  # ---------------------- Info
  def get_task_info(self, task_id: str) -> dict:
    return self.get_task(task_id).info()

  # ---------------------- Output
  def get_task_output(
    self,
    task_id: str,
    *args,
    **options,
  ) -> list:
    return self.get_task(task_id).get_task_output(
      *args,
      **options,
    )

  def clear_task_output(self, task_id: str) -> None:
    self.get_task(task_id).clear_output()

  # ---------------------- Close
  async def on_close(self) -> None:
    if not self.active_tasks:
      return

    logger.info(
      "Shutting down %d tasks | app=%s | app_id=%s",
      len(self.active_tasks),
      self.app_name,
      self.app_id,
    )

    # Kill all remaining subprocesses.
    for task in list(self.active_tasks.values()):
      await task.clean()

    self.active_tasks.clear()

    logger.info(
      "All tasks closed | app=%s | app_id=%s",
      self.app_name,
      self.app_id,
    )