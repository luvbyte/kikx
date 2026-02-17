import os
import sys
import pwd
import shlex
import signal
import asyncio
import logging

from uuid import uuid4
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Union

from core.func import funcx
from core.errors import raise_error
from core.func.handlers import Handler

from lib.parser import parse_config


logger = logging.getLogger(__name__)


class TasksConfigModel(BaseModel):
  shell: bool = False
  # KIKX_ env variables
  kikx: bool = True
  # If this is False then uses program env
  sandbox: bool = False
  # env variables in key/values
  env: Dict[str, str] = {}
  # Main program to run while running tasks
  main: str = Field('python3 -u $KIKX_APP_PATH/tasks/{name}.py {args}', description="Prefix for all tasks")

class Task:
  def __init__(self, cmd: str, env: Dict[str, str], shell: bool, cwd: str, sudo: bool):
    self.cmd: str = cmd
    self.cwd = cwd
    self.shell = shell
    self.env: Dict[str, str] = env
    self.id: str = uuid4().hex
    self.started: bool = False
    self.process: Optional[asyncio.subprocess.Process] = None
    self.stdout_timeout: int = 30
    self.waiting: bool = False
    self.task_input: List[str] = []
    
    # root / nobody - user
    self.sudo = sudo

    self.stdout = asyncio.subprocess.PIPE
    self.stdin = asyncio.subprocess.PIPE
    self.stderr = asyncio.subprocess.PIPE
    
    self.sid: Optional[int] = None
    self.pgid: Optional[int] = None
    
    self._cleaned = False
  
  def get_user(self):
    return "root" if self.sudo else "nobody"

  def demote(self, user_name):
    def result():
      pw = pwd.getpwnam(user_name)
      os.setgid(pw.pw_gid)
      os.setuid(pw.pw_uid)
    return result

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
    
    if self.sudo:
      preexec = None  # stay root
    else:
      preexec = self.demote(self.get_user())

    if self.shell:
      self.process = await asyncio.create_subprocess_shell(
        self.cmd,
        env=self.env,
        stdout=self.stdout,
        stdin=self.stdin,
        stderr=self.stderr,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec
      )
    else:
      self.process = await asyncio.create_subprocess_exec(
        *shlex.split(self.cmd),
        env=self.env,
        stdout=self.stdout,
        stdin=self.stdin,
        stderr=self.stderr,
        cwd=self.cwd,
        start_new_session=True,
        preexec_fn=preexec
      )
    self.started = True
    self.sid = os.getsid(self.process.pid)
    self.pgid = os.getpgid(self.process.pid)
    logger.info(f"Task started: {self.id} with command: {self.cmd}")
    
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

  # under testing
  async def run_quick(self, input_text: Optional[str] = None):
    """Run subprocess once and optionally send input."""
    if self.shell:
      proc = await asyncio.create_subprocess_shell(
        self.cmd,
        env=self.env,
        cwd=self.cwd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True
      )
    else:
      proc = await asyncio.create_subprocess_exec(
        *shlex.split(self.cmd),
        env=self.env,
        cwd=self.cwd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True
      )

    input_bytes = input_text.encode() if input_text else None
    stdout, stderr = await proc.communicate(input=input_bytes)

    return {
      "stdout": stdout.decode().strip(),
      "stderr": stderr.decode().strip(),
      "returncode": proc.returncode
    }
  
  # force kill with sigint fastest
  async def _force_kill(self):
    if not self.process or self.process.returncode is not None:
      logger.info(f"Task {self.id} already finished")
      return

    try:
      os.killpg(self.pgid, signal.SIGKILL)
      logger.warning(f"Task {self.id} (SID {self.sid}) forcefully killed")
    except Exception as e:
      logger.error(f"Force kill failed for {self.id}: {e}")

  # sending sigint + sigkill
  async def _force_gracefully_clean(self):
    if not self.process or self.process.returncode is not None:
      logger.info(f"Task {self.id} already finished")
      return

    try:
      os.killpg(self.pgid, signal.SIGINT)  # Try graceful stop
      await asyncio.wait_for(self.process.wait(), timeout=5)
      logger.info(f"Task {self.id} closed gracefully.")
    except asyncio.TimeoutError:
      os.killpg(self.pgid, signal.SIGKILL)  # Force kill if it hangs
      logger.warning(f"Task {self.id} forcefully killed after timeout.")
    except Exception as e:
      logger.error(f"Force kill failed for {self.id}: {e}")

  # gracefully + force 
  async def _clean_process(self, graceful_timeout: int = 3) -> None:
    if not self.process or self.process.returncode is not None:
      logger.info(f"Task {self.id} already finished")
      return
    try:
      # Try graceful shutdown
      self.process.terminate()
      await asyncio.wait_for(self.process.wait(), timeout=graceful_timeout)
      logger.info(f"Task closed gracefully -- {self.id}")
    except asyncio.TimeoutError:
      # os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
      await self._force_gracefully_clean()
      logger.warning(f"Task forcefully killed after timeout -- {self.id}")
    except Exception as e:
      # Catch any unexpected errors (e.g., process no longer exists)
      logger.error(f"Error cleaning task {self.id}: {e}")

  async def clean(self) -> None:
    if self._cleaned:
      return
    await self._force_kill()
    self._cleaned = True

class Tasks:
  def __init__(self, app, config):
     # tasks config {}
    self.config = TasksConfigModel(**config) 
    self.app_path = app.app_path
    self.task_cwd = str(app.get_app_data_path())
    
    # If not sandbox then copies program env
    self.task_env = {} if self.config.sandbox else os.environ.copy()

    if self.config.kikx:
      self.task_env.update({
        "KIKX_APP_ID": app.id,
        "KIKX_APP_NAME": app.name,
        "KIKX_STORAGE_PATH": str(app.user.storage_path),
        "KIKX_APP_PATH": str(app.get_app_path()),
        "KIKX_APP_DATA_PATH": str(app.get_app_data_path()),
        "KIKX_HOME_PATH": str(app.get_home_path()),
      })

    # Updating env with user env values
    self.task_env.update(self.config.env)

    # Program paths
    self.task_env.update({
      # 1. app/bin | 2. storage/bin | 3. kikx path
      "PATH": f'{str(self.app_path / "bin")}:{app.user.get_path_env()}:{str(Path(sys.executable).parent)}:{self.task_env.get("PATH", "")}'
    })
    
    # Sudo
    self.sudo = app.sudo #

    self.task_template: str = self.config.main
    self.send_event = app.send_event
    
    self.running_tasks: Dict[str, Task] = {}
    self.ctasks: List[asyncio.Task] = []

  def __on_ctask_complete(self, task: asyncio.Task) -> None:
    """Callback when a task is finished."""
    if task in self.ctasks:
      logger.info(f"CTask completed: {task}")
      self.ctasks.remove(task)

  async def _run_task(self, task: Task, handler: Handler):
    """Run and monitor the task."""
    try:
      await handler.started("Task started\n")
      return await task.run(handler)
    except Exception as e:
      logger.exception(f"Error while running task {task.id}")
      await handler.error(str(e))
    except asyncio.CancelledError:
      logger.info(f"CTask cancelled: {task.id}")
    finally:
      await task.clean()
      self.running_tasks.pop(task.id, None)

      await handler.ended("CTask ended\n")

  @funcx
  async def run_task(self, task_cmd: str, handler_id: str):
    """Public entry to start a task."""
    split_cmd = shlex.split(task_cmd)
    if not split_cmd:
      raise_error("Command not found")

    task_cmd = self.task_template.format_map({
      "name": split_cmd[0],
      "args": " ".join(split_cmd[1:])
    })

    task = Task(task_cmd, self.task_env, self.config.shell, self.task_cwd, self.sudo)

    self.running_tasks[task.id] = task
    ctask = asyncio.create_task(self._run_task(task, Handler(handler_id, self.send_event)), name=task.id)
    ctask.add_done_callback(self.__on_ctask_complete)
    self.ctasks.append(ctask)

    return task.id

  @funcx # 
  async def run_once(self, task_cmd: str, task_input: Optional[str] = None):
    split_cmd = shlex.split(task_cmd)
    if not split_cmd:
      raise_error("Command not found")

    task_cmd = self.task_template.format_map({
      "name": split_cmd[0],
      "args": " ".join(split_cmd[1:])
    })

    task = Task(task_cmd, self.task_env, self.config.shell, self.task_cwd, self.sudo)

    async def _runner():
      try:
        return await task.run_quick(task_input)
      except asyncio.CancelledError:
        logger.info(f"Task {task.id} was cancelled — terminating subprocess.")
        try:
          await task.clean()  # ensures process group is killed
        except Exception as ce:
          logger.warning(f"Error cleaning cancelled task {task.id}: {ce}")
        raise  # re-raise so asyncio knows it was cancelled
      except Exception as e:
        logger.exception(f"Error running task {task.id}: {e}")
        try:
          await task.clean()
        except Exception as ce:
          logger.warning(f"Error cleaning failed task {task.id}: {ce}")

    ctask = asyncio.create_task(_runner(), name=task.id)
    ctask.add_done_callback(self.__on_ctask_complete)
    self.ctasks.append(ctask)

    return await ctask

  @funcx
  async def kill(self, task_id: str) -> None:
    """Cancel a running task."""
    ctask = next((t for t in self.ctasks if t.get_name() == task_id), None)
    if ctask:
      ctask.cancel()
      logger.info(f"Cancelled Ctask {task_id}")

  @funcx
  async def send_input(self, task_id: str, input_text: str) -> None:
    """Send input to a running task."""
    task = self.running_tasks.get(task_id)
    if not task:
      raise_error("Task not found")
    await task.send(input_text)

  async def on_close(self) -> None:
    """Cancel and clean all background tasks safely."""
    if not self.ctasks:
      return

    logger.info("Shutting down all running tasks...")

    # Cancel all asyncio tasks
    for t in list(self.ctasks):
      t.cancel()

    # Wait briefly for cooperative exit
    done, pending = await asyncio.wait(self.ctasks, timeout=1.5)
    for p in pending:
      logger.warning(f"Force-cancelling {p.get_name()}")
      p.cancel()

    # Ensure subprocesses are killed
    for task in list(self.running_tasks.values()):
      await task.clean()

    logger.info("All tasks closed cleanly.")

