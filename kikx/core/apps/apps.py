from fastapi import WebSocket
from pathlib import Path
from uuid import uuid4
import asyncio
import signal
import os

from core.errors import raise_error
from lib.utils import is_websocket_connected, ensure_dir
from lib.parser import parse_config
from typing import Dict, Optional
from pydantic import BaseModel
from lib.utils import dynamic_import

from core.config.models import AppModel
from .modules.tasks import Tasks

from core.func import FuncX, funcx, funcx_handler


class App(FuncX):
  def __init__(self, client_id: str, name: str, app_path: Path, config: AppModel, user):
    super().__init__()
    self.name = name
    self.id = uuid4().hex
    # apps/[app]
    self.user = user # user object
    
    self.app_path = app_path  # current app path
    self.client_id = client_id
  
    self.config = config # app config like permissions & others
    self.title = self.config.title
    # self.config = parse_config(self.app_path / "config.json", AppRootConfigModel)
    self.websocket: Optional[WebSocket] = None
    # default env for task_template
    # adding tasks module
    self.__modules = []
    # load app required modules on startup
    self.load_modules()

  @property
  def connected(self):
    return is_websocket_connected(self.websocket)
    
  def load_modules(self):
    modules_list = set(self.config.modules)
    for module_name in modules_list:
      module = dynamic_import(f"app_{module_name}", f"./core/apps/modules/{module_name}.py")
      module_obj = getattr(module, module_name.capitalize())(self)

      setattr(self, module_name, module_obj)
      
      self.__modules.append({
        "name": module_name,
        "module": module,
        "obj": module_obj
      })
      print("Added app module ", module_name)

  # check permissions (remove no use)
  def has_permission(self, permission):
    # storage.<permission>
    if permission.startswith("storage.") and permission.split(".", 1)[1] in set(self.config.storage):
      return True
    return False

  # create paths if not exists
  def get_app_path(self):
    return self.app_path

  # create paths if not exists
  def get_home_path(self):
    # check permission and raise error
    return self.user.home_path
  
  # ---++-------- websockets
  # create paths if not exists
  def get_app_data_path(self):
    return ensure_dir(self.user.data_path / "data" / self.name)

  def connect_websocket(self, websocket: WebSocket):
    self.websocket = websocket if isinstance(websocket, WebSocket) else None
  
  # used to send to websocket
  async def send(self, data):
    if self.connected:
      await self.websocket.send_json(data)
    else:
      print(f"{self.name} : cant send data websocket not connected")
  
  # used to send to websocket
  async def send_event(self, event: str, payload):
    await self.send({"event": event, "payload": payload})

  @funcx
  async def echo(self, *args, **kwargs):
    pass

  async def on_close(self):
    await asyncio.gather(*[getattr(self, f"{module['name']}").on_close() for module in self.__modules], return_exceptions=True)
    await super().on_close()

  def __str__(self):
    return f"{self.name} - {self.id}"
