import os
import shlex
import signal
import asyncio
import logging

from uuid import uuid4
from typing import Dict, Optional, List, Union

from core.errors import raise_error
from core.func import funcx
from core.func.handlers import Handler


logger = logging.getLogger(__name__)


class Task:
  def __init__(self, cmd: str, env: Dict[str, str]):
    self.cmd: str = cmd
    self.env: Dict[str, str] = env
    self.id: str = uuid4().hex
    self.started: bool = False
    self.process: Optional[asyncio.subprocess.Process] = None
    self.stdout_timeout: int = 30
    self.waiting: bool = False
    self.task_input: List[str] = []

    self.stdout = asyncio.subprocess.PIPE
    self.stdin = asyncio.subprocess.PIPE
    self.stderr = asyncio.subprocess.PIPE

  async def send(self, data: str) -> None:
    """Send input to the subprocess."""
    if not self.process or self.process.returncode is not None:
      raise_error("No active process")

    self.process.stdin.write(data.encode() + b'\n')
    await self.process.stdin.drain()

  async def run(self, handler: Handler) -> Union[str, Dict[str, Optional[str]]]:
    """Start the subprocess and handle its output."""
    if self.started or self.process:
      await handler.error("Can't re-run task that's already running")
      raise_error("Can't re-run task that's already running")

    self.process = await asyncio.create_subprocess_shell(
      self.cmd,
      env=self.env,
      stdout=self.stdout,
      stdin=self.stdin,
      stderr=self.stderr,
      cwd=self.env.get("KIKX_APP_DATA_PATH"),
      start_new_session=True
    )
    self.started = True
    logger.info(f"Task started: {self.id} with command: {self.cmd}")

    if self.waiting:
      stdout, stderr = await self.process.communicate('\n'.join(self.task_input).encode())
      return {
        "stdout": stdout.decode() if stdout else None,
        "stderr": stderr.decode() if stderr else None
      }

    while True:
      try:
        stdout_line = await asyncio.wait_for(self.process.stdout.readline(), timeout=self.stdout_timeout)
        if not stdout_line:
          break
        await handler.output(stdout_line.decode())
      except asyncio.TimeoutError:
        await handler.info(f"Task {self.id}: No output for {self.stdout_timeout} seconds, checking process...\n")
        if self.process.returncode is not None:
          break

    await self.process.wait()
    stderr = await self.process.stderr.read()
    if stderr:
      await handler.error(stderr.decode())
    return self.id

  async def __clean__old(self) -> None:
    """Try graceful shutdown, fallback to force kill."""
    if not self.process or self.process.returncode is not None:
      logger.info(f"Task {self.id} already finished")
      return

    self.process.terminate()
    try:
      await asyncio.wait_for(self.process.wait(), timeout=5)
      logger.info(f"Task closed gracefully -- {self.id}")
    except asyncio.TimeoutError:
      os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
      logger.warning(f"Task force closed -- {self.id}")

  async def clean(self) -> None:
    """Force kill the subprocess."""
    if not self.process or self.process.returncode is not None:
      return
    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
    logger.warning(f"Task forcefully killed -- {self.id}")


class Tasks:
  def __init__(self, app):
    self.app_path = app.app_path
    self.task_env: Dict[str, str] = os.environ.copy()
    app_bin_path = self.app_path / 'bin'

    self.task_env.update({
      "PATH": f'{app_bin_path.as_posix()}:{app.user.get_path_env()}:{(app.user.home_path.parent.parent / "venv/bin").as_posix()}:{self.task_env["PATH"]}'
    })

    self.task_env.update({
      "KIKX_APP_ID": app.id,
      "KIKX_APP_NAME": app.name,
      "KIKX_STORAGE_PATH": app.user.storage_path.as_posix(),
      "KIKX_APP_PATH": app.get_app_path().as_posix(),
      "KIKX_APP_DATA_PATH": app.get_app_data_path().as_posix(),
      "KIKX_HOME_PATH": app.get_home_path().as_posix()
    })

    self.task_template: str = app.config.task_template
    self.send_event = app.send_event
    self.running_tasks: Dict[str, Task] = {}
    self.ctasks: List[asyncio.Task] = []

  def __on_task_complete(self, task: asyncio.Task) -> None:
    """Callback when a task is finished."""
    if task in self.ctasks:
      self.ctasks.remove(task)

  async def _run_task(self, task: Task, handler: Handler) -> Optional[Union[str, Dict[str, Optional[str]]]]:
    """Run and monitor the task."""
    try:
      await handler.started("Task started\n")
      return await task.run(handler)
    except Exception as e:
      logger.exception(f"Error while running task {task.id}")
      await handler.error(str(e))
    except asyncio.CancelledError:
      logger.info(f"Task cancelled: {task.id}")
    finally:
      await task.clean()
      self.running_tasks.pop(task.id, None)
      await handler.ended("Task ended\n")

  @funcx
  async def run_task(self, task_cmd: str, handler_id: Optional[str] = None, task_input: List[str] = []) -> Union[str, Dict[str, Optional[str]]]:
    """Public entry to start a task."""
    split_cmd = shlex.split(task_cmd)
    if not split_cmd:
      raise_error("Command not found")

    task_cmd = self.task_template.format_map({
      "name": split_cmd[0],
      "args": shlex.join(split_cmd[1:])
    })

    task = Task(task_cmd, self.task_env)

    if handler_id is None:
      task.waiting = True
      task.task_input = task_input

    self.running_tasks[task.id] = task
    ctask = asyncio.create_task(self._run_task(task, Handler(handler_id, self.send_event)), name=task.id)
    ctask.add_done_callback(self.__on_task_complete)
    self.ctasks.append(ctask)

    return await ctask if handler_id is None else task.id

  @funcx
  async def kill(self, task_id: str) -> None:
    """Cancel a running task."""
    ctask = next((t for t in self.ctasks if t.get_name() == task_id), None)
    if ctask:
      ctask.cancel()
      logger.info(f"Cancelled task {task_id}")

  @funcx
  async def sh(self, task_cmd: str, task_input: List[str] = []) -> Dict[str, Optional[str]]:
    """Shortcut to run a shell command with input and wait."""
    return await self.run_task(task_cmd, task_input=task_input)

  @funcx
  async def send_input(self, task_id: str, input_text: str) -> None:
    """Send input to a running task."""
    task = self.running_tasks.get(task_id)
    if not task:
      raise_error("Task not found")
    await task.send(input_text)

  async def on_close(self) -> None:
    """Cancel all tasks when shutting down."""
    for ctask in self.ctasks:
      ctask.cancel()
