import inspect
import asyncio


# Events
class Events:
  def __init__(self):
    self._events = {}

  def add_event(self, event: str, handler):
    if event not in self._events:
      self._events[event] = []
    self._events[event].append(handler)

  async def emit_order(self, event: str, *args):
    handlers = self._events.get(event, [])
    for handler in handlers:
      if inspect.iscoroutinefunction(handler):
        await handler(*args)
      else:
        handler(*args)

  async def emit(self, event: str, *args):
    handlers = self._events.get(event, [])
    tasks = []

    for handler in handlers:
      if inspect.iscoroutinefunction(handler):
        tasks.append(handler(*args))
      else:
        handler(*args)

    if tasks:
      await asyncio.gather(*tasks)

  async def emit_async(self, event: str, *args):
    task = asyncio.create_task(self.emit(event, *args))
    task.add_done_callback(self._handle_task_result)

  def _handle_task_result(self, task: asyncio.Task):
    try:
      task.result()
    except Exception as e:
      print(f"Event handler error: {e}")
