import functools
import asyncio
import logging
from typing import Dict, Callable, Any, Awaitable
from uuid import uuid4


class Handler:
  """Handler that manages event messages and statuses."""
  def __init__(self, handler_id: str, send_event: Callable[[str, dict], Awaitable[None]]):
    self.id = handler_id
    self.send_event = send_event

  async def send(self, status: str, output: Any):
    """Send data with a specific status."""
    if self.id is None:
      return
    try:
      await self.send_event("handler-data", {"id": self.id, "data": {"status": status, "output": output}})
    except Exception:
      pass

  async def started(self, message: Any):
    await self.send("started", message)

  async def info(self, message: Any):
    await self.send("info", message)

  async def output(self, message: Any):
    await self.send("output", message)

  async def error(self, message: Any):
    await self.send("error", message)

  async def ended(self, message: Any):
    await self.send("ended", message)

def create_handler(handler_id, send_event):
  return Handler(handler_id, send_event)
