import asyncio
import logging

from pathlib import Path
from typing import Any

from fastapi import WebSocket

from core.app import App
from core.connection import Connection
from core.models.app import AppManifestModel, AppModel, AppOptionsModel
from core.ui import ClientUI

from lib.utils import generate_uuid, get_timestamp, joinpath


logger = logging.getLogger(__name__)


# ---------------------- Client
class Client:
  def __init__(
    self,
    user: Any,
    resolve_path,
    access_token: str,
    ui_name: str,
  ) -> None:
    super().__init__()

    self.id: str = generate_uuid()
    self.created_at: str = get_timestamp()
    self.user: Any = user
    self.access_token: str = access_token
    self.ui: ClientUI = ClientUI(ui_name, self.user.load_ui_config(ui_name))
    self.connection: Connection = Connection("Client")
    self.apps_path: Path = resolve_path("apps://")
    self.running_apps: dict[str, App] = {}

    logger.info(
      f"Client initialized (ID: {self.id}) with (UI: {self.ui.name})"
    )

  @property
  def name(self) -> str:
    return self.ui.name

  @property
  def apps_count(self) -> int:
    return len(self.running_apps)

  # ---------------------- Apps
  def get_app(self, app_id: str) -> App:
    app = self.running_apps.get(app_id)

    if app is None:
      raise Exception("App not found")

    return app

  def info(self) -> dict[str, Any]:
    return {
      "id": self.id,
      "name": self.name,
      "user": self.user.user_data,
      "created_at": self.created_at,
      "access_token": self.access_token,
      "connection": self.connection.info(),
      "apps_count": self.apps_count,
      "apps": [app.info() for app in self.running_apps.values()],
    }

  def open_app(
    self,
    name: str,
    manifest: AppManifestModel,
    options: AppOptionsModel | dict,
  ) -> App:
    logger.info(f"App Start ({name}) using (Options: {options})")

    app_path = joinpath(self.apps_path, name)
    app_config: AppModel = self.user.load_app_config(name)

    app = App(
      self.id,
      name,
      app_path,
      app_config,
      self.user,
      manifest,
      options,
    )

    self.running_apps[app.id] = app
    return app

  async def close_app(self, app: App) -> None:
    await app.on_close()
    del self.running_apps[app.id]

    logger.info(
      f"App Closed ({app.name}) (ID: {app.id}) (Client: {app.client_id})"
    )

  # ---------------------- WebSocket
  async def connect_websocket(self, websocket: WebSocket) -> None:
    await self.connection.connect(websocket)

  async def send_event(self, event: str, payload: Any) -> None:
    logger.info(f"Sending client event: {event}")
    await self.connection.send_event(event, payload)

  async def broadcast_to_apps(self, event: str, payload: dict) -> None:
    await asyncio.gather(
      *(app.send_event(event, payload) for app in self.running_apps.values()),
      return_exceptions=True,
    )

  # ---------------------- Close
  async def on_close(self) -> None:
    logger.info(f"Client Closing ({self.id})")

    await asyncio.gather(
      *(app.on_close() for app in self.running_apps.values()),
      return_exceptions=True,
    )

    self.running_apps.clear()

    try:
      await asyncio.wait_for(self.connection.close(1008), timeout=2)
    except asyncio.TimeoutError:
      logger.warning(
        f"Client({self.id}) Timed out while closing connection."
      )

    logger.info(f"Client Closed ({self.id})")

  def __str__(self) -> str:
    return (
      f"Client (ID: {self.id}) "
      f"(UI: {self.ui.name}) "
      f"(Apps: {self.apps_count})"
    )