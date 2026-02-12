import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

from lib.parser import parse_config
from core.errors import raise_error
from core.models.user_models import UserDataModel
from core.models.setting_models import UserSettingsModel

logger = logging.getLogger(__name__)


class User:
  """Represents a single user's profile and configuration."""

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

    logger.info(f"User loaded: {self.username}")

  def get_path_env(self) -> str:
    """Return path to user's binary folder."""
    return (self.storage_path / 'bin').as_posix()

  def get_app_config_file_path(self, app_id: str) -> Path:
    """Return the config path for a specific app. Raise error if missing."""
    app_config = self.data_path / "app" / f"{app_id}.json"
    if not app_config.exists():
      raise_error("App config not found")
    return app_config

  def get_installed_apps(self) -> list[str]:
    """List all app folders from user storage."""
    apps = os.listdir(self.storage_path / 'apps')
    logger.debug(f"Installed apps: {apps}")
    return apps

  def on_close(self) -> None:
    """Trigger user-level shutdown handlers (e.g., save settings)."""
    logger.info(f"User {self.username} session closed")
