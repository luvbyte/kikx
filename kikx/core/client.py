import asyncio
from typing import Dict, Optional

from core.apps import App
from core.ui import ClientUI
from core.func import FuncX, funcx
from core.connection import Connection
from core.func.handlers import Handler
from core.models.app_models import AppModel

from lib.parser import parse_config
from lib.utils import generate_uuid, get_timestamp, joinpath

from pathlib import Path

from fastapi import WebSocket

from core.logging import Logger



logging = Logger("kikx_clients", "kikx_clients.log")
logger = logging.get_logger()


class Client(FuncX):
  """
  Represents a connected client that manages multiple apps and handles communication.
  """
  def __init__(self, user: object, resolve_path: callable, access_token: str, ui: ClientUI):
    super().__init__()
    self.id: str = generate_uuid()
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
  
  # Send event to client connection only if connected else stores
  async def send_event(self, event: str, payload: dict) -> None:
    """Sends an event to the client's connection"""
    logger.info(f"Sending event to client: {event}")
    await self.connection.send_event(event, payload)
  
  # Open app 
  def open_app(self, name: str, manifest, sudo) -> App:
    """
    Opens an app for the client by name.
    Loads its configuration and creates the App instance.
    """
    logger.info(f"Opening app: {name}")
    
    app_path = joinpath(self.apps_path, name)
    # app config
    app_config: AppModel = self.user.load_app_config(name)

    app = App(self.id, name, app_path, app_config, self.user, manifest, sudo)
    self.running_apps[app.id] = app

    logger.info(f"App opened: {app.name} (ID: {app.id})")
    return app

  # Close app 
  async def close_app(self, app: App) -> None:
    """
    Closes a specific app and removes it from the running list.
    """
    await app.on_close()
    del self.running_apps[app.id]

    logger.info(f"App closed: {app.name}")
    logger.info(f"Remaining active apps: {list(self.running_apps.keys())}")

  async def on_close(self) -> None:
    """
    Cleans up all apps and resources when the client disconnects.
    """
    logger.info(f"Closing client: {self.id}")
    
    # Closing parent funcx
    await super().on_close()

    # Closing apps
    await asyncio.gather(
      *(app.on_close() for app in self.running_apps.values()),
      return_exceptions=True
    )
    
    # Clearing running apps list
    self.running_apps.clear()
    logger.info(f"All apps shut down for client {self.id}")

  # Broadcast event to apps
  async def broadcast_to_apps(self, event, payload):
    """Broadcast event to apps"""
    await asyncio.gather(
      *(app.send_event(event, payload) for app in self.running_apps.values()),
      return_exceptions=True
    )

  def __str__(self) -> str:
    return f"Client (ID : {self.id}) (UI: {self.ui.name})"
