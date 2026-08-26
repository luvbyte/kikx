from typing import Any
from pathlib import Path

from utils import get_root_path

from core.storage import Storage
from core.models.kikx_models import RootConfigModel

from lib.utils import ensure_dir, joinpath
from lib.parser import parse_config



# Cant uninstall but can update
ADMIN_APPS = [
  "com.kikx.appstore",
  "com.kikx.sessions",
  "com.kikx.explorer"
]


class Config:
  """Main configuration manager for storage, paths, and app access."""

  def __init__(self, storage: str) -> None:
    self._storage: Storage = Storage(storage)
    self._kikx: RootConfigModel = parse_config(
      self.resolve_path("storage://config/kikx.json"), RootConfigModel
    )

  @property
  def admin_apps(self) -> list[str]:
    return ADMIN_APPS
  
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
      }
    }

  def resolve_path(self, line: str) -> Path:
    """Resolves custom protocol paths to absolute storage paths."""
    if "://" not in line:
      return Path(line)

    protocol, path = line.split("://", 1)

    match protocol:
      case "root":
        return self.storage.join(path)
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
      case "os":
        return joinpath(Path.home(), path)
      case "osr":
        return joinpath(Path.cwd().anchor, path)
      case _:
        return Path(line)

  @property
  def storage(self) -> Storage:
    return self._storage

  @property
  def kikx(self) -> RootConfigModel:
    """Returns the parsed kikx root config."""
    return self._kikx

  @property
  def storage_path(self) -> Path:
    return ensure_dir(self.storage.path)

  @property
  def home_path(self) -> Path:
    """Returns home path (storage://home)."""
    return ensure_dir(self.resolve_path("storage://home"))

  @property
  def share_path(self) -> Path:
    """Returns global shared path (storage://share)."""
    return ensure_dir(self.resolve_path("storage://share"))

  @property
  def files_path(self) -> Path:
    """Returns shared files path (home://share)."""
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

  def get_apps_list(self) -> list[Path]:
    """Returns a list of all app directories under apps path."""
    return list(self.apps_path.glob("*/"))
