import json

from pathlib import Path
from pydantic import Field, BaseModel

from core.models.kikx_models import RootConfigModel, ServicesConfigModel
from core.models.user_models import UserAuthModel, UserDataModel



class SetupConfigModel(BaseModel):
  kikx: RootConfigModel = Field(default_factory=RootConfigModel)
  auth: UserAuthModel = Field(default_factory=UserAuthModel)
  services: ServicesConfigModel = Field(default_factory=ServicesConfigModel)
  user_data: UserDataModel = Field(default_factory=UserDataModel)

# Set-up FS 
class SetupFS:
  def __init__(self, path: str | Path):
    self.fs_path: Path = Path(path)
    self.fs_path.mkdir(parents=True, exist_ok=True)

    self._pre_create_paths = [
      "apps", "bin", "config",
      "data/app", "data/config", "data/data",
      "etc", "home", "temp", "ui", "logs",
      "share/images/bg", "home/share/images/bg"
    ]

  def ensure_dir(self, path, parents=True, exist_ok=True) -> Path:
    path = self.fs_path / path
    path.mkdir(parents=parents, exist_ok=exist_ok)

    return path

  def ensure_dirs(self, *paths) -> None:
    for path in paths:
      self.ensure_dir(path)

  def pre_create(self):
    self.ensure_dirs(*self._pre_create_paths)

  def create_config(self, path: Path, data) -> None:
    path.write_text(data.model_dump_json(indent=2), encoding="utf-8")

  def setup_config(self, config):
    config = SetupConfigModel(**config)

    # kikx.json
    self.create_config(
      self.fs_path / "config" / "kikx.json",
      config.kikx
    )
    # config/auth.json
    self.create_config(
      self.fs_path / "config" / "auth.json",
      config.auth
    )
    # config/services.json
    self.create_config(
      self.fs_path / "config" / "services.json",
      config.services
    )
    # data/config/user_data.json
    self.create_config(
      self.fs_path / "data" / "config" / "user_data.json",
      config.user_data
    )
