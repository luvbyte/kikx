from typing import Any
from pathlib import Path

from core.models.user_models import UserDataModel, UserAuthModel
from core.models.app_models import AppManifestModel, AppModel
from core.models.ui_models import UIConfigModel

from lib.utils import joinpath
from lib.parser import parse_config

from fastapi import HTTPException


class User:
  def __init__(
    self,
    user_config: UserAuthModel,
    kikx_config,
  ) -> None:
    self.config: UserAuthModel = user_config
    self.kikx_config = kikx_config

    self.user_data: UserDataModel = parse_config(
      self.data_path / "config/user_data.json", UserDataModel
    )

  @property
  def storage_path(self) -> Path:
    return self.kikx_config.storage_path
  
  @property
  def home_path(self) -> Path:
    return self.kikx_config.home_path
  
  @property
  def data_path(self) -> Path:
    return self.kikx_config.data_path

  @property
  def apps_path(self) -> Path:
    return self.kikx_config.apps_path

  @property
  def uis_path(self) -> Path:
    return self.kikx_config.uis_path

  @property
  def apps_data_path(self) -> Path:
    return self.kikx_config.apps_data_path

  def info(self) -> dict[str, Any]:
    return {
      "config": self.config.model_dump(),
      "data": self.user_data.model_dump()
    }

  # storage/bin path
  def get_path_env(self) -> str:
    return (self.storage_path / 'bin').as_posix()

  # App config in /data/<name>.json or error
  def get_app_config_file_path(self, app_name: str) -> Path:
    app_config_path = joinpath(self.apps_data_path, f"{app_name}.json")
    if not app_config_path.is_file():
      raise Exception("App config file not found")

    return app_config_path
  
  # Save
  def save_app_config(self, app_name: str, config: AppModel | dict, indent: int = 2) -> None:
    obj = config if isinstance(config, AppModel) else AppModel(**config)
    self.get_app_config_file_path(app_name).write_text(obj.model_dump_json(indent=indent))

  def load_app_config(self, app_name: str) -> AppModel:
    return parse_config(self.get_app_config_file_path(app_name), AppModel)
  
  def load_ui_config(self, ui_name: str) -> UIConfigModel:
    return parse_config(
      joinpath(self.uis_path, ui_name, "ui.json"),
      UIConfigModel
    )

  # Return installed apps in list
  def get_installed_apps(self, raw: bool = False, both: bool = False) -> list[str]:
    return [p.name for p in self.apps_path.iterdir() if p.is_dir()]

  # if not found raise error
  def check_app_exists(self, app_name: str) -> None:
    if app_name not in self.get_installed_apps():
      raise Exception("App not found")

  async def on_close(self, core) -> None:
    pass
