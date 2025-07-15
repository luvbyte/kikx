from lib.parser import parse_config
from datetime import datetime
import json
from pathlib import Path
from core.config.models import UserDataModel
from core.errors import raise_error, Error, ClientError, AppError, TaskError
import os

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
