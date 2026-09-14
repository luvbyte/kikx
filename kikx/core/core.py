import asyncio
import logging

from typing import Any

from fastapi import FastAPI

from core.__about__ import __author__, __version__
from core.app import App
from core.auth import Auth
from core.client import Client
from core.config import Config
from core.console import Console
from core.os import OS
from core.services import Services
from core.user import User

from core.setup.apps import setup_apps
from core.setup.ui import setup_ui
from core.utils import load_app_manifest

from lib.event import Events


logger = logging.getLogger(__name__)


# ---------------------- Core
class Core:
  def __init__(self, storage_path: str, dev_mode: bool) -> None:
    self._dev_mode: bool = dev_mode
    self.precheck = not dev_mode

    self.config: Config = Config(storage_path)

    self.events: Events = Events()
    self.auth: Auth = Auth(self.config)
    self.user: User = User(self.config)
    self.scr: Console = Console()
    self.os = OS()

    self.clients: dict[str, Client] = {}
    self.app_index: dict[str, str] = {}

    self.services: Services = Services(self.config)

  @property
  def version(self) -> str:
    return __version__

  @property
  def author(self) -> str:
    return __author__

  @property
  def is_dev_mode(self) -> bool:
    return self._dev_mode

  # ---------------------- Clients
  def get_admin_apps_list(self) -> list[str]:
    return list(self.config.admin_apps)

  def get_client(self, client_id: str) -> Client | None:
    return self.clients.get(client_id)

  def get_client_app_by_id(
    self,
    app_id: str,
  ) -> tuple[Client | None, App | None]:
    client_id = self.app_index.get(app_id)

    if client_id is None:
      return None, None

    client = self.clients.get(client_id)

    if client is None:
      return None, None

    app = client.running_apps.get(app_id)
    return (client, app) if app else (None, None)

  # ---------------------- Apps
  def get_apps_by_name(self, name: str) -> list[App]:
    return [
      app
      for client in self.clients.values()
      for app in client.running_apps.values()
      if app.name == name
    ]

  def get_installed_apps(self, raw: bool = False, both: bool = False) -> list:
    def safe_load(name):
      try:
        return load_app_manifest(self, name, raw=raw, both=both)
      except Exception:
        return None

    return [
      result
      for name in self.user.get_installed_apps()
      if (result := safe_load(name)) is not None
    ]

  def is_app_installed(self, name: str) -> bool:
    return name in self.user.get_installed_apps()

  async def open_app(self, client_id: str, name: str, options) -> Any:
    client = self.get_client(client_id)

    if client is None:
      raise Exception("Client not found")

    info, manifest = load_app_manifest(self, name, both=True)

    app = client.open_app(name, manifest, options)
    self.app_index[app.id] = client.id

    await self.events.emit_async("app:open", app.id, app.name)

    return app, info

  async def close_app(self, client: Client, app: App) -> None:
    await client.close_app(app)
    self.app_index.pop(app.id, None)

    await self.events.emit_async("app:close", app.id, app.name)

  # ---------------------- Client Connection
  async def on_client_connect(
    self,
    access_token,
    ui,
  ) -> Client:
    client = Client(
      self.user,
      self.config.resolve_path,
      access_token,
      ui,
    )

    self.clients[client.id] = client

    await self.events.emit_async("client:connect", client.id, ui)

    return client

  async def on_client_close(self, client: Client) -> None:
    apps_list = [
      (app.id, app.name)
      for app in client.running_apps.values()
    ]

    await client.on_close()
    self.clients.pop(client.id, None)

    for app_id, name in apps_list:
      self.app_index.pop(app_id, None)
      await self.events.emit_async("app:close", app_id, name)

    await self.events.emit_async("client:close", client.id)

  async def close_client(self, client_id: str) -> None:
    client = self.get_client(client_id)

    if client is None:
      raise Exception("Client not found")

    await self.on_client_close(client)

  # ---------------------- WebSocket Data
  async def on_app_data(
    self,
    client: Client,
    app: App,
    data: dict,
  ) -> None:
    pass

  async def on_client_data(self, client: Client, data: dict) -> None:
    pass

  # ---------------------- Lifecycle
  async def on_start(self, app: FastAPI) -> None:
    await self.services.load(self, app)

    if self.precheck:
      await setup_ui(self)
      await setup_apps(self)

    await self.events.emit_order("kikx:start", self)

  async def on_close(self) -> None:
    for client in list(self.clients.values()):
      await self.on_client_close(client)

    await self.services.on_close(self)
    await self.user.on_close(self)

    await self.events.emit_order("kikx:close", self)

  # ---------------------- Broadcast
  async def broadcast_to_clients(
    self,
    event: str,
    payload=None,
    ignore_clients=None,
  ) -> None:
    ignore = set(ignore_clients or {})

    await asyncio.gather(
      *(
        client.send_event(event, payload)
        for client in self.clients.values()
        if client.id not in ignore
      ),
      return_exceptions=True,
    )

  async def broadcast_to_apps(
    self,
    event: str,
    payload: dict,
    client_id: str | None = None,
  ) -> None:
    if client_id is None:
      await asyncio.gather(
        *(
          client.broadcast_to_apps(event, payload)
          for client in self.clients.values()
        ),
        return_exceptions=True,
      )
      return

    client = self.get_client(client_id)

    if client is None:
      raise Exception("Client not found")

    await client.broadcast_to_apps(event, payload)