import os
import logging
from typing import Any
from pathlib import Path
from datetime import datetime

from lib.utils import joinpath
from lib.parser import parse_config

from core.models.user_models import UserDataModel
from core.models.app_models import AppManifestModel, AppModel



class User:
  def __init__(
    self,
    user_config: Any,
    user_data_path: Path,
    home_path: Path,
    storage_path: Path
  ):
    self.config = user_config
    self.username: str = user_config.name

    self.data_path: Path = user_data_path
    self.home_path: Path = home_path
    self.storage_path: Path = storage_path

    self.user_data: UserDataModel = parse_config(
      self.data_path / "config/user_data.json", UserDataModel
    )

    self.apps_path = (self.storage_path / "apps").resolve()
    self.apps_data_path = (self.data_path / "app").resolve()

  # storage/bin path
  def get_path_env(self) -> str:
    return (self.storage_path / 'bin').as_posix()

  # App config in /data/<name>.json or error
  def get_app_config_file_path(self, app_name: str) -> Path:
    """Return the config path for a specific app. Raise error if missing."""
    app_config_path = joinpath(self.apps_data_path, f"{app_name}.json")
    if not app_config_path.is_file():
      raise Exception("App config file not found")

    return app_config_path

  # Return installed apps in list
  def get_installed_apps(self) -> list[str]:
    """Return installed apps list"""
    return [path.name for path in self.apps_path.iterdir() if path.is_dir()]
  
  # if not found raise error
  def check_app_exists(self, app_name: str):
    if app_name not in self.get_installed_apps():
      raise Exception("App not found")

  # Return app manifest if not found raise error
  def load_app_manifest(self, app_name: str) -> AppManifestModel:
    # raise if not found
    self.check_app_exists(app_name)

    manifest_path = joinpath(self.apps_path, app_name, "app.json")
    return parse_config(manifest_path, AppManifestModel)

  # Return app config if not found raise error
  def load_app_config(self, app_name: str) -> AppModel:
    # raise if not found
    self.check_app_exists(app_name)

    return parse_config(self.get_app_config_file_path(app_name), AppModel)

  async def on_close(self, core) -> None:
    pass
