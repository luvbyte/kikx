from pathlib import Path
from typing import Any

from config.setup import ADMIN_APPS, ADMIN_UIS
from core.models.kikx import (
  AuthModel,
  KikxConfigModel,
  ServerModel,
  ServicesConfigModel,
  UserDataModel,
)
from core.storage import Storage
from lib.parser import ParseConfig
from lib.utils import ensure_dir, joinpath
from utils import get_root_path


# ---------------------- Config
class Config:
  """Main configuration manager for storage, paths, and app access."""

  def __init__(self, storage: str) -> None:
    self._storage: Storage = Storage(storage)

    self.kikx_config_path = self.resolve_path("storage://config/kikx.json")
    self.kikx_config = ParseConfig(
      self.kikx_config_path,
      KikxConfigModel,
      lorc=True,
    )

  @property
  def admin_apps(self) -> list[str]:
    return ADMIN_APPS

  @property
  def admin_uis(self) -> list[str]:
    return ADMIN_UIS

  @property
  def storage(self) -> Storage:
    return self._storage

  @property
  def kikx(self) -> KikxConfigModel:
    return self.kikx_config.data

  @property
  def auth(self) -> AuthModel:
    return self.kikx.auth

  @property
  def user(self) -> UserDataModel:
    return self.kikx.user

  @property
  def services(self) -> ServicesConfigModel:
    return self.kikx.services

  @property
  def server(self) -> ServerModel:
    return self.kikx.server

  # ---------------------- Paths
  @property
  def storage_path(self) -> Path:
    return ensure_dir(self.storage.path)

  @property
  def home_path(self) -> Path:
    return ensure_dir(self.resolve_path("storage://home"))

  @property
  def share_path(self) -> Path:
    return ensure_dir(self.resolve_path("storage://share"))

  @property
  def temp_path(self) -> Path:
    return ensure_dir(self.resolve_path("storage://temp"))

  @property
  def files_path(self) -> Path:
    return ensure_dir(self.resolve_path("home://share"))

  @property
  def apps_path(self) -> Path:
    return ensure_dir(self.resolve_path("apps://"))

  @property
  def uis_path(self) -> Path:
    return ensure_dir(self.resolve_path("storage://ui"))

  @property
  def data_path(self) -> Path:
    return ensure_dir(self.resolve_path("storage://data"))

  @property
  def apps_data_path(self) -> Path:
    return ensure_dir(self.resolve_path("storage://data/app"))

  # ---------------------- Apps
  def get_apps_list(self) -> list[Path]:
    return list(self.apps_path.glob("*/"))

  # ---------------------- Config
  def get_kikx_config(self, reset: bool = False) -> dict:
    if reset:
      self.kikx_config.set_default_config()

    return self.kikx.model_dump()

  def update_kikx_config(self, config) -> None:
    for field in config.model_fields_set:
      setattr(self.kikx_config._data, field, getattr(config, field))

    self.kikx_config.save()

  def info(self) -> dict[str, Any]:
    return {
      "storage": self.storage.info(),
      "kikx": self.kikx.model_dump(),
      "apps_list": [str(path) for path in self.get_apps_list()],
      "paths": {
        "share_path": str(self.share_path),
        "files_path": str(self.files_path),
        "apps_path": str(self.apps_path),
        "uis_path": str(self.uis_path),
        "data_path": str(self.data_path),
        "apps_data_path": str(self.apps_data_path),
      },
    }

  # ---------------------- Resolve Path
  def resolve_path(self, line: str) -> Path:
    if "://" not in line:
      return Path(line)

    protocol, path = line.split("://", 1)

    match protocol:
      case "root" | "storage":
        return self.storage.join(path)
      case "share":
        return self.storage.join("share", path)
      case "apps":
        return self.storage.join("apps", path)
      case "data":
        return self.storage.join("data", path)
      case "home":
        return self.storage.join("home", path)
      case "kikx":
        return joinpath(get_root_path(), path)
      case "os":
        return joinpath(Path.home(), path)
      case "osr":
        return joinpath(Path.cwd().anchor, path)
      case _:
        return Path(line)