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



class UserSettings:
  def __init__(self, settings_path):
    self.settings_path = settings_path
  
  @property
  def raw(self):
    return parse_config(self.settings_path)
  
  @property
  def parsed(self):
    return { i["id"]: i["value"] for i in self.raw["kikx"] }
    
  def _convert_value(self, value, field_type):
    try:
      if field_type == "number":
        return int(value)
      elif field_type == "date":
        # Validates format 'YYYY-MM-DD'
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
      elif field_type == "checkbox":
        if isinstance(value, bool):
          return value
        return str(value).lower() in ["true", "1", "yes", "on"]
      elif field_type in ["radio", "select"]:
        return str(value)
      elif field_type == "email":
        if "@" in value:
          return str(value)
        else:
          raise ValueError("Invalid email format")
      elif field_type in ["text", "textarea", "password"]:
        return str(value)
      else:
        return value
    except Exception as e:
      raise ValueError(f"Type conversion failed for type '{field_type}' with value '{value}': {e}")

  def update(self, new_values):
    settings = self.raw["kikx"]

    id_to_setting = {setting['id']: setting for setting in settings}
  
    for key, new_val in new_values.items():
      if key in id_to_setting:
        setting = id_to_setting[key]
        field_type = setting.get("type", "text")
  
        try:
          converted_value = self._convert_value(new_val, field_type)
  
          if field_type in ["radio", "select"] and "options" in setting:
            if converted_value not in setting["options"]:
              raise ValueError(f"Invalid option '{converted_value}' for field '{key}'")
  
          setting["value"] = converted_value
  
        except ValueError as err:
          print(f"Warning: {err}")
      
    with open(self.settings_path, "w") as file:
      json.dump({ "kikx": settings }, file)

class User:
  def __init__(self, user_config, user_data_path, home_path, storage_path):
    self.config = user_config
    self.username = user_config.username

    # user all paths
    self.data_path: Path = user_data_path # data://users# app data folder
    self.home_path = home_path  # home://{user_id}/ # home folder or sdcard folder
    self.storage_path = storage_path # storage path
    
    # has user data
    self.user_data = parse_config(self.data_path / "config/user_data.json", UserDataModel)

    # settings
    self.settings = UserSettings(self.data_path / "config/settings.json")

  # returns env pat
  def get_path_env(self):
    return (self.storage_path / 'bin').as_posix()

  # returns app_config content
  def get_app_config_file_path(self, app_id):
    app_config = self.data_path / "app" / f"{app_id}.json"
    if not app_config.exists():
      raise_error("App config not found")
    return app_config

  # list 
  def get_installed_apps(self) -> list[str]:
    return os.listdir(self.storage_path / 'apps')
  
  # update settings
  def update_setting(self, name, value):
    pass

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
