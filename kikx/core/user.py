from pathlib import Path

from core.models.kikx import UserDataModel
from core.models.app import AppModel
from core.models.ui import UIConfigModel

from lib.utils import joinpath
from lib.parser import parse_config


class User:
  def __init__(self, kikx_config) -> None:
    self.kikx_config = kikx_config

  @property
  def user_data(self) -> UserDataModel:
    return self.kikx_config.user

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

  # storage/bin path
  def get_path_env(self) -> str:
    return str(self.storage_path / "bin")

  # App config in /data/<name>.json
  def get_app_config_file_path(self, app_name: str) -> Path:
    app_config_path = joinpath(self.apps_data_path, f"{app_name}.json")

    if not app_config_path.is_file():
      raise Exception("App config file not found")

    return app_config_path

  # Save app config
  def save_app_config(self, app_name: str, config: AppModel | dict, indent: int = 2) -> None:
    obj = config if isinstance(config, AppModel) else AppModel(**config)
    self.get_app_config_file_path(app_name).write_text(obj.model_dump_json(indent=indent))

  # Load app config
  def load_app_config(self, app_name: str) -> AppModel:
    return parse_config(self.get_app_config_file_path(app_name), AppModel)

  def get_installed_uis(self) -> list[str]:
    return [p.name for p in self.uis_path.iterdir() if p.is_dir()]

  def is_ui_exists(self, name):
    return name in self.get_installed_uis()

  # Load ui config
  def load_ui_config(self, ui_name: str) -> UIConfigModel:
    return parse_config(joinpath(self.uis_path, ui_name, "ui.json"), UIConfigModel)

  # Return installed apps list
  def get_installed_apps(self, raw: bool = False, both: bool = False) -> list[str]:
    return [p.name for p in self.apps_path.iterdir() if p.is_dir()]

  # if not found raise error
  def check_app_exists(self, app_name: str) -> None:
    if app_name not in self.get_installed_apps():
      raise Exception("App not found")

  async def on_close(self, core) -> None:
    pass