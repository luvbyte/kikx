import asyncio
import logging

from pathlib import Path
from typing import Callable, Any

from fastapi import WebSocket

from core.apps import App
from core.ui import ClientUI
from core.func import FuncX, funcx
from core.connection import Connection
from core.models.app_models import AppModel

from lib.utils import generate_uuid, get_timestamp, joinpath



logger = logging.getLogger(__name__)



class Client(FuncX):
  """
  Represents a connected client that manages multiple apps and handles communication.
  """
  def __init__(self, user: Any, resolve_path: Callable, access_token: str, ui_name: str) -> None:
    super().__init__()
    self.id: str = generate_uuid()

    self.user: Any = user
    self.access_token: str = access_token
    
    self.ui: ClientUI = ClientUI(ui_name, self.user.load_ui_config(ui_name))

    self.connection: Connection = Connection("Client")

    self.created_at: str = get_timestamp()

    self.apps_path: Path = resolve_path("apps://")
    self.running_apps: dict[str, App] = {}

    logger.info(f"Client initialized (ID: {self.id}) with (UI: {self.ui.name})")
  
  @property
  def name(self) -> str:
    return self.ui.name

  def get_app(self, app_id: str) -> App:
    return self.running_apps[app_id]

  def get_app_config(self, app: str | App) -> dict:
    if isinstance(app, str):
      app = self.get_app(app)

    return { **app.config.model_dump(), "ui": self.ui.name  }

  async def connect_websocket(self, websocket: WebSocket) -> None:
    await self.connection.connect(websocket)

  def info(self) -> dict[str, Any]:
    return {
      "id": self.id,
      "name": self.name,
      "user": self.user.user_data,
      "created_at": self.created_at,
      "access_token": self.access_token,
      "connection": self.connection.info(),
      "apps": [app.info() for app in self.running_apps.values()]
    }

  # Send event to client connection only if connected else stores
  async def send_event(self, event: str, payload: Any) -> None:
    """Sends an event to the client's connection"""
    logger.info(f"Sending event to client: {event}")
    await self.connection.send_event(event, payload)
  
  # Open app 
  def open_app(self, name: str, manifest: Any, options: Any) -> App:
    """
    Opens an app for the client by name.
    Loads its configuration and creates the App instance.
    """
    logger.info(f"Opening app: {name}")
    
    app_path = joinpath(self.apps_path, name)
    
    # app config
    app_config: AppModel = self.user.load_app_config(name)

    app = App(self.id, name, app_path, app_config, self.user, manifest, options)
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

  # Broadcast event to apps
  async def broadcast_to_apps(self, event: str, payload: Any):
    """Broadcast event to apps"""
    await asyncio.gather(
      *(app.send_event(event, payload) for app in self.running_apps.values()),
      return_exceptions=True
    )
  
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
    
    # Try closing connection
    try:
      await asyncio.wait_for(self.connection.close(1008), timeout=2)
    except asyncio.TimeoutError:
      logger.warning("Timed out while closing connection from client.")

  def __str__(self) -> str:
    return f"Client (ID : {self.id}) (UI: {self.ui.name})"
