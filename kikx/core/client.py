import asyncio
import logging

from pathlib import Path
from typing import Callable, Any

from fastapi import WebSocket

from core.app import App
from core.ui import ClientUI
from core.func import FuncX, funcx
from core.connection import Connection
from core.models.app_models import AppModel, AppOptionsModel, AppManifestModel

from lib.utils import generate_uuid, get_timestamp, joinpath



logger = logging.getLogger(__name__)



class Client(FuncX):
  """
  Represents a connected client that manages multiple apps and handles communication.
  """
  def __init__(self, user: Any, resolve_path: Callable, access_token: str, ui_name: str) -> None:
    super().__init__()
    
    # Client ID
    self.id: str = generate_uuid()
    # Created timestamp
    self.created_at: str = get_timestamp()
    # User object
    self.user: Any = user
    # Access Token
    self.access_token: str = access_token
    # UI Object
    self.ui: ClientUI = ClientUI(ui_name, self.user.load_ui_config(ui_name))
    # Connection Object
    self.connection: Connection = Connection("Client")
    # Apps path
    self.apps_path: Path = resolve_path("apps://")
    # Running apps list
    self.running_apps: dict[str, App] = {}

    logger.info(f"Client initialized (ID: {self.id}) with (UI: {self.ui.name})")
  
  @property
  def name(self) -> str:
    return self.ui.name

  @property
  def apps_count(self) -> str:
    return len(self.running_apps)

  # Get running app
  def get_app(self, app_id: str) -> App:
    app = self.running_apps.get(app_id, None)
    if app is None:
      raise Exception("App not found")
  
    return app
  
  # Get app config by name / App object
  def get_app_config(self, app: str | App) -> dict:
    if isinstance(app, str):
      app = self.get_app(app)

    return { **app.config.model_dump(), "ui": self.ui.name  }
  
  # Get client info object
  def info(self) -> dict[str, Any]:
    return {
      "id": self.id,
      "name": self.name,
      "user": self.user.user_data,
      "created_at": self.created_at,
      "access_token": self.access_token,
      "connection": self.connection.info(),
      "apps_count": self.apps_count,
      "apps": [app.info() for app in self.running_apps.values()]
    }

  # Connect websocket connection
  async def connect_websocket(self, websocket: WebSocket) -> None:
    await self.connection.connect(websocket)

  # Send event to client connection
  async def send_event(self, event: str, payload: Any) -> None:
    logger.info(f"Sending client event: {event}")
    
    await self.connection.send_event(event, payload)

  # Open app
  def open_app(self, name: str, manifest: AppManifestModel, options: AppOptionsModel | dict) -> App:
    logger.info(f"App Start ({name}) using (Options: {options})")
    
    # Safe join
    app_path = joinpath(self.apps_path, name)

    # app config
    app_config: AppModel = self.user.load_app_config(name)

    app = App(self.id, name, app_path, app_config, self.user, manifest, options)
    self.running_apps[app.id] = app

    return app

  # Close app 
  async def close_app(self, app: App) -> None:
    await app.on_close()
    del self.running_apps[app.id]

    logger.info(f"App Closed ({app.name}) (ID: {app.id}) (Client: {app.client_id})")

  # Broadcast event to running apps
  async def broadcast_to_apps(self, event: str, payload: dict):
    await asyncio.gather(
      *(app.send_event(event, payload) for app in self.running_apps.values()),
      return_exceptions=True
    )
  
  # Cleanup
  async def on_close(self) -> None:
    logger.info(f"Client Closing ({self.id})")

    # Closing parent funcx
    await super().on_close()

    # Closing apps
    await asyncio.gather(
      *(app.on_close() for app in self.running_apps.values()),
      return_exceptions=True
    )

    # Clearing running apps list
    self.running_apps.clear()

    # Try closing connection
    try:
      await asyncio.wait_for(self.connection.close(1008), timeout=2)
    except asyncio.TimeoutError:
      logger.warning(f"Client({self.id}) Timed out while closing connection.")
    
    logger.info(f"Client Closed ({self.id})")

  def __str__(self) -> str:
    return f"Client (ID: {self.id}) (UI: {self.ui.name}) (Apps: {self.apps_count})"
