import asyncio
import functools
import logging
from uuid import uuid4
from typing import Any, Callable, List, Optional

from pydantic import BaseModel, Field

from .handlers import Handler  # Placeholder for future use
from .models import FuncXConfig, FuncXModel
from core.errors import raise_error


logger = logging.getLogger(__name__)


class XFunction:
  """Wrapper for binding instance methods dynamically."""

  def __init__(self, func: Callable):
    self.func = func
    self.is_handler = False  # Reserved for future use

  def __call__(self, *args, **kwargs):
    return self.func(*args, **kwargs)

  def __get__(self, instance, owner):
    if instance is None:
      return self.func
    return XFunction(functools.partial(self.func, instance))


def funcx(func: Callable) -> XFunction:
  """Decorator to expose methods as async callable."""
  return XFunction(func)


def funcx_handler(func: Callable):
  """Reserved for handler-based funcx extensions."""
  # No-op for now, future use for streaming or UI handlers
  return func


class FuncX:
  """Base class to enable dynamic function execution from client."""

  def __init__(self):
    self.__funcx_tasks: List[asyncio.Task] = []

  async def send_event(self, event: str, data: Any):
    """Override in subclass to send events (e.g. over websocket)."""
    pass

  @funcx
  async def cancel_funcx(self, funcx_id: str):
    """Cancel a running funcx task by ID (unimplemented)."""
    # Needs task lookup by ID to cancel specific task
    pass

  def __on_funcx_task_complete(self, task: asyncio.Task):
    """Callback for when a task completes."""
    if task in self.__funcx_tasks:
      self.__funcx_tasks.remove(task)
    logger.info(f"Funcx task complete: {task.get_name()}")

  async def _run_func(self, func: Callable, config: FuncXConfig) -> Any:
    """Run a registered async function with optional timeout."""
    task_id = uuid4().hex
    task = asyncio.create_task(func(*config.args, **config.options), name=task_id)
    task.add_done_callback(self.__on_funcx_task_complete)
    self.__funcx_tasks.append(task)

    try:
      if config.timeout > 0:
        return await asyncio.wait_for(task, timeout=config.timeout)
      return await task
    except asyncio.TimeoutError:
      logger.warning(f"Funcx task timed out: {task.get_name()}")
      raise_error("Timeout")
    except asyncio.CancelledError:
      logger.info(f"Funcx task cancelled: {task.get_name()}")
    except Exception as e:
      logger.exception("Unhandled exception in funcx task")
      raise_error(str(e))

  async def run_function(self, func_model: FuncXModel) -> Any:
    """Resolve and run a function via dot-path (e.g. module.sub.func)."""
    *attrs, name = func_model.name.split(".")
    obj = self

    for attr in attrs:
      obj = getattr(obj, attr, None)
      if obj is None:
        raise_error(f"'{attr}' not found in '{'.'.join(attrs)}'")

    func = getattr(obj, name, None)

    if isinstance(func, XFunction):
      return await self._run_func(func, func_model.config)

    raise_error("Function not found")

  async def on_close(self):
    """Cancel all active funcx tasks."""
    for task in self.__funcx_tasks:
      task.cancel()
    logger.info("Funcx closed: all tasks cancelled")

