import logging
from uuid import uuid4
from typing import Dict
from core.apps import App
from lib.utils import is_websocket_connected
from lib.parser import parse_config
from core.config.models import UserModel, AppModel, UserDataModel
from core.errors import raise_error, Error, ClientError, AppError, TaskError
from pathlib import Path
from functools import reduce
from datetime import datetime
import os
import json

from core.config.models import UserSettingsModel

from core.func.handlers import Handler
from core.func import FuncX, funcx

logging.basicConfig(level=logging.INFO, format="\n%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# client
class Client(FuncX):
  def __init__(self, user, resolve_path, websocket):
    super().__init__()
    self.id = uuid4().hex

    self.user = user

    self.websocket = websocket
    self.apps_path = resolve_path("apps://")
  
    # apps opened by client
    self.running_apps: Dict[str, App] = {}
  
  @funcx
  async def user_data(self):
    return self.user.user_data
  
  @funcx
  async def user_settings(self):
    return self.user.settings
  
  @funcx
  async def echo(self, *args, **options):
    return { "args": args, "options": options }

  # sends event to client
  async def send_event(self, event, payload):
    if is_websocket_connected(self.websocket):
      await self.websocket.send_json({
        "event": event, "payload": payload
      })

  # open app
  def open_app(self, name):
    # if app_config not found for user if uses default config located in private/permissions.json
    app_path = self.apps_path / name
    if not app_path.exists() or not app_path.is_dir():
      raise_error("App not found in apps reinstall")
  
    try:
      app_config_file_path = self.user.get_app_config_file_path(name)
      app_config = parse_config(app_config_file_path, AppModel)
    except Exception:
      raise_error("Error parsing app config file")
    # adding paths for env
    app = App(self.id, name, app_path, app_config, self.user)
    self.running_apps[app.id] = app
    return app

  async def close_app(self, app):
    await app.on_close()
    del self.running_apps[app.id]
    
    logger.info("App closed")
    logger.info(f"Active Apps {self.running_apps}")

  # remove all apps
  # optimize
  async def on_close(self):
    # clean for FuncX
    await super().on_close()

    for app in list(self.running_apps.values()):
      await app.on_close()
    #self.running_apps.clear()
    
    del self.running_apps

  def __str__(self):
    return f"( ID : {self.id} )"
