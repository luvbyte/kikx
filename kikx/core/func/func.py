from .handlers import Handler
from core.errors import raise_error
import functools
import asyncio
from uuid import uuid4
# from core.models import FuncXModel

from pydantic import BaseModel, Field

class FuncXConfig(BaseModel):
  args: list = []
  options: dict = {}
  
  timeout: int = 0

class FuncXModel(BaseModel):
  name: str
  config: FuncXConfig = Field(default_factory=FuncXConfig)

class XFunction:
  def __init__(self, func):
    self.func = func
    self.is_handler = False

  def __call__(self, *args, **kwargs):
    return self.func(*args, **kwargs)
  
  def __get__(self, instance, owner):
    """Ensure that the function binds `self` correctly when used in a class."""
    if instance is None:
      return self.func  # Accessing from class
    return XFunction(functools.partial(self.func, instance))  # Bind `self`

def funcx(func):
  return XFunction(func)

def funcx_handler(func):
  pass

# exposes functions to frontend
class FuncX:
  def __init__(self):
    # running couroutine handlers
    self.__funcx_tasks = []

  # should implement child obj
  async def send_event(self, event, data):
    pass
  
  # cancels funcx_handler function
  @funcx
  async def cancel_funcx(self, funcx_id):
    pass

  def __on_funcx_task_complete(self, task):
    self.__funcx_tasks.remove(task)
    print("Funcx_tasks : ", self.__funcx_tasks)

  # run function
  async def _run_func(self, func, config: FuncXConfig):
    task_id = uuid4().hex
    task = asyncio.create_task(func(*config.args, **config.options), name=task_id)
    task.add_done_callback(self.__on_funcx_task_complete)
    
    self.__funcx_tasks.append(task)
    
    if config.timeout > 0:
      try:
        return await asyncio.wait_for(task, timeout=config.timeout)
      # timeout error
      except asyncio.TimeoutError:
        raise_error("Timeout")
      # task canceled by closing app or something
      except asyncio.exceptions.CancelledError:
        pass
      except Exception as e:
        raise_error(str(e))
    else:
      return await task

  # reserved dont override this 
  async def run_function(self, func_model: FuncXModel):
    print(func_model)
    *attrs, name = func_model.name.split(".")  # Split the path, extracting the command
    obj = self

    # Traverse the object hierarchy dynamically
    for attr in attrs:
      obj = getattr(obj, attr, None)
      if obj is None:
        raise AttributeError(f"'{attr}' not found in '{'.'.join(attrs)}'")
    # Locate the method with prefix
    func = getattr(obj, name, None)
    if isinstance(func, XFunction):
      return await self._run_func(func, func_model.config)
    else:
      raise_error("Function not found")

  # this will clear all running
  async def on_close(self):
    for task in self.__funcx_tasks:
      task.cancel()

