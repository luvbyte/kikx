import inspect
import asyncio

from typing import Any

def _filtered_args(handler, args):
  sig = inspect.signature(handler)

  # Count positional parameters
  positional = [
    p for p in sig.parameters.values()
    if p.kind in (
      inspect.Parameter.POSITIONAL_ONLY,
      inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
  ]

  # If handler accepts *args, pass everything
  has_varargs = any(
    p.kind == inspect.Parameter.VAR_POSITIONAL
    for p in sig.parameters.values()
  )

  if has_varargs:
    return args

  return args[:len(positional)]

# Events
class Events:
  def __init__(self) -> None:
    self._events: dict[str, Any] = {}
  
  # Registered Events Info
  def info(self) -> dict[str, Any]:
    return {
      "registered": { name: len(f_list) for name, f_list in self._events.items() }
    }
  
  # Add event handler
  def add_event(self, event: str, handler) -> None:
    if event not in self._events:
      self._events[event] = []
    self._events[event].append(handler)

  # Emit events in order
  async def emit_order(self, event: str, *args) -> None:
    handlers = self._events.get(event, [])
    for handler in handlers:
      call_args = _filtered_args(handler, args)
      
      if inspect.iscoroutinefunction(handler):
        await handler(*call_args)
      else:
        handler(*call_args)
  
  # Emit event
  async def emit(self, event: str, *args) -> None:
    handlers = self._events.get(event, [])
    tasks = []

    for handler in handlers:
      call_args = _filtered_args(handler, args)
      
      if inspect.iscoroutinefunction(handler):
        tasks.append(handler(*call_args))
      else:
        handler(*call_args)

    if tasks:
      await asyncio.gather(*tasks)

  # Emit async
  async def emit_async(self, event: str, *args, callback=None) -> None:
    task = asyncio.create_task(self.emit(event, *args))
    task.add_done_callback(callback or self._handle_task_result)
  
  # Handle async emit handler results
  def _handle_task_result(self, task):
    if task.cancelled():
      return

    try:
      task.result()
    except Exception as e:
      print(f"Task failed in Events: {e}")
