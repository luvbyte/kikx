import sys
import asyncio

from lib.event import Events


class KikxServer:
  def __init__(self, config):
    self.config = config
    self.events = Events()
  
    self.process: asyncio.subprocess.Process | None = None
    
    self.stdout: list[str] = []
    
  @property
  def is_running(self) -> bool:
    return self.process is not None and self.process.returncode is None
  
  async def _stdout(self, message):
    self.stdout.append(message)
    await self.events.emit("stdout", message)

  async def _start(self):
    if self.is_running:
      raise RuntimeError("Kikx server is already running")

    self.process = await asyncio.create_subprocess_exec(
      sys.executable,
      "-u",
      "main.py",
      stdin=asyncio.subprocess.PIPE,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.STDOUT,
    )

    while True:
      line = await self.process.stdout.readline()

      if not line:
        break

      await self._stdout(line.decode(errors="replace"))

  async def start(self):
    asyncio.create_task(self._start())

  async def stop(self):
    process = self.process

    if process is None:
      return

    if process.returncode is None:
      process.terminate()

      try:
        await asyncio.wait_for(process.wait(), timeout=10)
      except asyncio.TimeoutError:
        process.kill()
        await process.wait()

    self.process = None
  
  def get_stdout(self):
    return self.stdout

  def get_status(self):
    return {
      "running": self.is_running,
      "pid": self.process.pid if self.process else None
    }
  
  async def on_close(self):
    await self.stop()

