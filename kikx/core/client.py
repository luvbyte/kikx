import asyncio
import logging
from uuid import uuid4
from typing import Dict, Optional

from core.apps import App
from core.errors import raise_error
from core.func import FuncX, funcx
from core.connection import Connection
from core.func.handlers import Handler
from core.models.app_models import AppModel

from core.ui import ClientUI

from lib.parser import parse_config

from lib.utils import get_timestamp

from pathlib import Path

from fastapi import WebSocket

logging.basicConfig(level=logging.INFO, format="\n%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Client(FuncX):
  """
  Represents a connected client that manages multiple apps and handles communication.
  """
  def __init__(self, user: object, resolve_path: callable, access_token: str, ui: ClientUI):
    super().__init__()
    self.id: str = uuid4().hex
    self.user: object = user
    self.access_token = access_token
    
    self.ui: ClientUI = ui

    self.connection: Connection = Connection()

    self.created_at: str = get_timestamp()

    self.apps_path: Path = resolve_path("apps://")
    self.running_apps: Dict[str, App] = {}

    logger.info(f"Client initialized (ID: {self.id}) with (UI: {self.ui.name})")
  
  def get_app(self, app_id: str) -> App:
    return self.running_apps[app_id]

  def get_app_config(self, app: str | App) -> dict:
    if isinstance(app, str):
      app = self.get_app(app)

    return { **app.config.model_dump(), "ui": self.ui.name  }

  async def connect_websocket(self, websocket):
    await self.connection.connect(websocket)

  @funcx
  async def user_data(self) -> dict:
    """Returns user's data."""
    return self.user.user_data

  @funcx # not required
  async def user_settings(self) -> dict:
    """Returns user's settings."""
    return self.user.settings
  
  @funcx
  async def info(self):
    return {
      "id": self.id,
      "user": self.user.user_data,
      "created_at": self.created_at,
      
      "access_token": self.access_token,

      "connection": self.connection.info(),

      "apps": [app.info() for app in self.running_apps.values()]
    }

  async def send_event(self, event: str, payload: dict) -> None:
    """Sends an event to the client's websocket."""
    logger.info(f"Sending event to client: {event}")
    await self.connection.send_event(event, payload)

  def open_app(self, name: str, manifest, sudo) -> App:
    """
    Opens an app for the client by name.
    Loads its configuration and creates the App instance.
    """
    logger.info(f"Opening app: {name}")
    app_path = self.apps_path / name
    if not app_path.exists() or not app_path.is_dir():
      logger.error(f"App not found: {name}")
      raise_error("App not found in apps reinstall")

    try:
      app_config_file_path = self.user.get_app_config_file_path(name)
      app_config: AppModel = parse_config(app_config_file_path, AppModel)
    except Exception as e:
      logger.error(f"Error parsing config for app '{name}': {e}")
      raise_error("Error parsing app config file")

    app = App(self.id, name, app_path, app_config, self.user, manifest, sudo)
    self.running_apps[app.id] = app
    logger.info(f"App opened: {app.name} (ID: {app.id})")
    return app

  async def close_app(self, app: App) -> None:
    """
    Closes a specific app and removes it from the running list.
    """
    logger.info(f"Closing app: {app.name} (ID: {app.id})")
    await app.on_close()
    del self.running_apps[app.id]

    logger.info(f"App closed: {app.name}")
    logger.info(f"Remaining active apps: {list(self.running_apps.keys())}")

  async def on_close(self) -> None:
    """
    Cleans up all apps and resources when the client disconnects.
    """
    logger.info(f"Closing client: {self.id}")
    await super().on_close()

    for app in list(self.running_apps.values()):
      logger.info(f"Shutting down app: {app.name} (ID: {app.id})")
      await app.on_close()

    self.running_apps.clear()
    logger.info(f"All apps shut down for client {self.id}")

  def __str__(self) -> str:
    return f"( ID : {self.id} )"
