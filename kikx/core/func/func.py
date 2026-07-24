import asyncio
import logging
import functools

from uuid import uuid4
from typing import Any

from .models import FuncXConfig, FuncXModel



logger = logging.getLogger(__name__)


class XFunction:
  """Wrapper for binding instance methods dynamically."""

  def __init__(self, func: Any) -> None:
    self.func = func
    self.is_handler = False  # Reserved for future use

  def __call__(self, *args, **kwargs):
    return self.func(*args, **kwargs)

  def __get__(self, instance, owner):
    if instance is None:
      return self.func
    return XFunction(functools.partial(self.func, instance))


def funcx(func: Any) -> XFunction:
  """Decorator to expose methods as async callable."""
  return XFunction(func)


def funcx_handler(func: Any) -> Any:
  """Reserved for handler-based funcx extensions."""
  # No-op for now, future use for streaming or UI handlers
  return func


class FuncX:
  """Base class to enable dynamic function execution from client."""

  def __init__(self) -> None:
    # List of waiting tasks to complete
    self.__funcx_tasks: list[asyncio.Task] = []
  
  @property
  def class_name(self):
    return self.__class__.__name__

  # placeholder function 
  async def send_event(self, event: str, data: Any) -> None:
    """Override in subclass to send events (e.g. over websocket)."""
    pass

  # remove task from list on complete
  def __on_funcx_task_complete(self, task: asyncio.Task) -> None:
    """Callback for when a task completes."""
    logger.info(f"Funcx({self.class_name}) task complete: {task.get_name()}")

    if task in self.__funcx_tasks:
      self.__funcx_tasks.remove(task)
      logger.info(f"Funcx({self.class_name}) task removed: {task.get_name()}")
  
  # wrapper function for funcx task core logic
  async def _run_func(self, func: Any, config: FuncXConfig) -> Any:
    """Run a registered async function with optional timeout."""
    task_id = uuid4().hex
    task = asyncio.create_task(func(*config.args, **config.options), name=task_id)
    task.add_done_callback(self.__on_funcx_task_complete)
    self.__funcx_tasks.append(task)
    
    logger.info(f"Funcx({self.class_name}) task running: {task_id}")

    try:
      if config.timeout > 0:
        return await asyncio.wait_for(task, timeout=config.timeout)
      return await task
    except asyncio.TimeoutError:
      logger.warning(f"Funcx({self.class_name}) task timed out: {task.get_name()}")
      raise # re-raise
    except asyncio.CancelledError:
      logger.info(f"Funcx({self.class_name}) task cancelled: {task.get_name()}")
      raise # re-raise
    except Exception:
      logger.exception(f"Funcx({self.class_name}) Exception in task")
      raise

  # Entry point for running funcx task
  async def run_function(self, func_model: FuncXModel) -> Any:
    """Resolve and run a function via dot-path (e.g. module.sub.func)."""
    *attrs, name = func_model.name.split(".")
    obj = self

    for attr in attrs:
      obj = getattr(obj, attr, None)
      if obj is None:
        raise Exception(f"'{attr}' not found in '{'.'.join(attrs)}'")

    func = getattr(obj, name, None)

    if isinstance(func, XFunction):
      return await self._run_func(func, func_model.config)

    raise Exception(f"Function not found: {func_model.name}")

  # When closing app / client
  async def on_close(self) -> None:
    """Cancel all active funcx tasks and wait for them to finish."""
    if not getattr(self, "__funcx_tasks", None):
      return
    
    # tasks must implement cancel checks
    for task in self.__funcx_tasks:
      task.cancel()
  
    try:
      await asyncio.wait_for(
        asyncio.gather(*self.__funcx_tasks, return_exceptions=True),
        timeout=2
      )
    except asyncio.TimeoutError:
      logger.warning(f"Funcx({self.class_name}) Some tasks did not cancel in time. Forcing shutdown.")
  
    logger.info(f"Funcx({self.class_name}) closed: all tasks cancelled")
