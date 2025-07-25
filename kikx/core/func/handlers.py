import asyncio
import functools
from typing import Any, Awaitable, Callable, Optional


class Handler:
  """Handler that manages event messages and statuses."""

  def __init__(self, handler_id: Optional[str], send_event: Callable[[str, dict], Awaitable[None]]):
    self.id: Optional[str] = handler_id
    self.send_event = send_event

  async def send(self, status: str, output: Any) -> None:
    """Send data with a specific status."""
    if self.id is None:
      return
    try:
      await self.send_event("handler-data", {
        "id": self.id,
        "data": {
          "status": status,
          "output": output
        }
      })
    except Exception:
      pass  # Fail silently

  async def started(self, message: Any) -> None:
    await self.send("started", message)

  async def info(self, message: Any) -> None:
    await self.send("info", message)

  async def output(self, message: Any) -> None:
    await self.send("output", message)

  async def error(self, message: Any) -> None:
    await self.send("error", message)

  async def ended(self, message: Any) -> None:
    await self.send("ended", message)


def create_handler(handler_id: Optional[str], send_event: Callable[[str, dict], Awaitable[None]]) -> Handler:
  """Factory method to create a handler."""
  return Handler(handler_id, send_event)
