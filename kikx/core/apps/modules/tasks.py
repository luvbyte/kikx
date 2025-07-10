from pathlib import Path
from uuid import uuid4
from typing import Dict, Optional
import asyncio
import os
import signal
import shlex

from core.errors import raise_error
from pydantic import BaseModel, Field

from core.func.handlers import Handler
from core.func import funcx


class Task:
  def __init__(self, cmd, env):
    self.cmd = cmd
    self.env = env
    self.id = uuid4().hex
    self.started = False
    self.process: Optional[asyncio.subprocess.Process] = None
    self.stdout_timeout = 30
    self.waiting = False
    self.task_input = []
    # self.shell = False
    self.stdout = asyncio.subprocess.PIPE
    self.stdin = asyncio.subprocess.PIPE
    self.stderr = asyncio.subprocess.PIPE

  async def send(self, data: str):
    if not self.process or self.process.returncode is not None:
      raise_error("No active process")

    self.process.stdin.write(str(data).encode() + b'\n')
    await self.process.stdin.drain()

  async def run(self, handler: Handler):
    if self.started or self.process:
      await handler.error("Can't re-run task that's already running")
      raise_error("Can't re-run task that's already running")

    # self.process = await asyncio.create_subprocess_exec(
    self.process = await asyncio.create_subprocess_shell(
      self.cmd,
      env=self.env,
      stdout=self.stdout,
      stdin=self.stdin,
      stderr=self.stderr,
      # !!!
      cwd=self.env.get("KIKX_APP_DATA_PATH", None),
      start_new_session=True
    )
    self.started = True

    if self.waiting:
      stdout, stderr = await self.process.communicate(('\n'.join(self.task_input)).encode())
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
      await handler.error(str(stderr.decode()))

    return self.id

  async def __clean__old(self):
    if not self.process or self.process.returncode is not None:
      print(f"Task {self.id} already finished")
      return
    
    #self.process.send_signal(signal.SIGINT)
    self.process.terminate()
    try:
      await asyncio.wait_for(self.process.wait(), timeout=5)
      print(f"Task closed gracefully -- {self.id}")
    except asyncio.TimeoutError:
      os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
      print(f"Task force closed -- {self.id}")
  async def clean(self):
    if not self.process or self.process.returncode is not None:
      print(f"Task {self.id} already finished")
      return

    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
    print(f"Task force closed -- {self.id}")

class Tasks:
  #def __init__(self, app_path, task_template, task_env, send_event):
  def __init__(self, app):
    self.app_path = app.app_path

    # configuring
    self.task_env = os.environ.copy()

    app_bin_path = self.app_path / 'bin'

    self.task_env.update({
      "PATH": f'{app_bin_path.as_posix()}:{app.user.get_path_env()}:{self.task_env["PATH"]}'
    })
  
    #self.default_task_env = {} # isolated from shell commands
    self.task_env.update({
      "KIKX_APP_ID": app.id,
      "KIKX_APP_NAME": app.name,
  
      "KIKX_STORAGE_PATH": app.user.storage_path.as_posix(),
      "KIKX_APP_PATH": app.get_app_path().as_posix(),
      "KIKX_APP_DATA_PATH": app.get_app_data_path().as_posix(),
      
      "PY_PATH": (app.user.home_path.parent.parent / "venv/bin/python3").as_posix(),
  
      "KIKX_HOME_PATH": app.get_home_path().as_posix()
    })
  
    self.task_template = app.config.task_template
    self.send_event = app.send_event
    
    self.running_tasks: Dict[str, Task] = {}
    self.ctasks = []

  def __on_task_complete(self, task: asyncio.Task):
    self.ctasks.remove(task)
    print("CTask complete:", self.ctasks)

  async def _run_task(self, task, handler):
    try:
      await handler.started("Task started\n")
      return await task.run(handler)
    except Exception as e:
      print(f"Exception: {str(e)}")
      await handler.error(str(e))
    except asyncio.CancelledError:
      print("Task canceled")
    finally:
      await task.clean()
      self.running_tasks.pop(task.id, None)
      await handler.ended("Task ended\n")
      print(f"Task {task.id} deleted\nRunning tasks: {self.running_tasks}")

  @funcx
  async def run_task(self, task_cmd: str, handler_id: Optional[str] = None, task_input=[]):
    #cmd = f"{self.task_template} {task_cmd} {args}"
    split_cmd = shlex.split(task_cmd)
    if len(split_cmd) < 1:
      raise_error("Command not found")

    task_cmd = self.task_template.format_map({
      "name": split_cmd[0],
      "args": shlex.join(split_cmd[1:])
    })
    print("Task CMD:", task_cmd)

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
  async def kill(self, task_id: str):
    # Find the associated asyncio.Task
    ctask = next((t for t in self.ctasks if t.get_name() == task_id), None)

    # Cancel the asyncio task if found
    if ctask:
      ctask.cancel()
      # self.ctasks.remove(ctask)

  @funcx
  async def sh(self, task_cmd: str, task_input=[]):
    return await self.run_task(task_cmd, task_input=task_input)

  @funcx
  async def send_input(self, task_id: str, input_text: str):
    task = self.running_tasks.get(task_id)
    if not task:
      raise_error("Task not found")
    return await task.send(input_text)

  async def on_close(self):
    for ctask in self.ctasks:
      ctask.cancel()
