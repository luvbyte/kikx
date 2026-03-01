import json
import logging
from pathlib import Path

from utils import get_root_path

from core.models.kikx_models import RootConfigModel
from core.storage import Storage

from lib.utils import ensure_dir, joinpath
from lib.parser import parse_config


# Cant uninstall but can update
ADMIN_APPS = { 
  "com.kikx.appstore",
  "com.kikx.sessions",
  "com.kikx.files"
}


class Config:
  """Main configuration manager for storage, paths, and app access."""

  def __init__(self, storage: str):
    self._storage: Storage = Storage(storage)
    self._kikx: RootConfigModel = parse_config(
      self.resolve_path("storage://config/kikx.json"), RootConfigModel
    )

  @property
  def admin_apps(self):
    return ADMIN_APPS

  def resolve_path(self, line: str) -> Path | str:
    """Resolves custom protocol paths to absolute storage paths."""
    splitted = line.split("://", 1)
    if len(splitted) <= 1:
      return line  # raw path

    protocol, path = splitted
    match protocol:
      case "storage":
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
      case _:
        return line

  @property
  def storage(self) -> Storage:
    return self._storage

  @property
  def kikx(self) -> RootConfigModel:
    """Returns the parsed kikx root config."""
    return self._kikx

  def get_apps_list(self) -> list[Path]:
    """Returns a list of all app directories under apps path."""
    return list(self.apps_path.glob("*/"))

  @property
  def share_path(self) -> Path:
    """Returns global shared path (storage://share)."""
    return ensure_dir(self.resolve_path("storage://share"))

  @property
  def files_path(self) -> Path:
    """Returns home-level shared files path (home://share)."""
    return ensure_dir(self.resolve_path("home://share"))

  @property
  def apps_path(self) -> Path:
    """Returns path to user app storage (apps://)."""
    return ensure_dir(self.resolve_path("apps://"))

  @property
  def uis_path(self) -> Path:
    """Returns ui's path"""
    return ensure_dir(self.resolve_path("storage://ui"))
  
  @property
  def data_path(self) -> Path:
    """Returns data path"""
    return ensure_dir(self.resolve_path("storage://data"))

  @property
  def apps_data_path(self) -> Path:
    """Returns app data path"""
    return ensure_dir(self.resolve_path("storage://data/app"))
