import asyncio
import logging

from pathlib import Path
from typing import Any

from fastapi import FastAPI

from core.app import App
from core.user import User
from core.auth import Auth
from core.config import Config
from core.client import Client
from core.console import Console
from core.services import Services
from core.__about__ import __version__, __author__

from core.setup.apps import setup_apps
from core.setup.ui import setup_ui
from core.utils import load_app_manifest

from lib.event import Events
from lib.process import sh


logger = logging.getLogger(__name__)

# -------------------------------------
# Core API
# -------------------------------------


class Core:
  def __init__(self, storage_path: str, dev_mode: bool) -> None:
    # Dev mode
    self._dev_mode: bool = dev_mode
    # Initialize Console
    self.scr: Console = Console()
    # Load configuration
    self.config: Config = Config(storage_path)

    # Run boot script if exists
    boot_file: Path = self.config.resolve_path("storage://etc/boot.sh")
    if boot_file.is_file():
      sh(f"chmod +x {boot_file} && {boot_file}").run(False)

    # Initialize Auth
    self.auth: Auth = Auth(self.config.resolve_path("storage://config/auth.json"))
    # Initialize User
    self.user: User = User(self.auth.user_config, self.config)
    # Clients and Apps Dict
    self.clients: dict[str, Client] = {}
    self.app_index: dict[str, str] = {}  # Maps app_id -> client_id
    # Events
    self.events: Events = Events()
    # Load services
    self.services: Services = Services(self.config.resolve_path("storage://config/services.json"))

  @property
  def version(self) -> str:
    return __version__

  @property
  def author(self) -> str:
    return __author__

  @property
  def is_dev_mode(self) -> bool:
    return self._dev_mode
  
  # Get admin apps list
  def get_admin_apps_list(self) -> list[str]:
    return list(self.config.admin_apps)

  # Get client by ID
  def get_client(self, client_id: str) -> Client | None:
    return self.clients.get(client_id, None)

  # Return the (client, app) tuple given an app ID.
  # Returns (None, None) if not found or invalid.
  def get_client_app_by_id(self, app_id: str) -> tuple[Client | None, App | None]:
    client_id = self.app_index.get(app_id)
    if client_id is None:
      return None, None

    client = self.clients.get(client_id)
    if client is None:
      return None, None

    app = client.running_apps.get(app_id)
    return (client, app) if app else (None, None)
  
  # Get all runnings apps list by name
  def get_apps_by_name(self, name: str) -> list:
    return [
      app
      for client in self.clients.values()
      for app in client.running_apps.values()
      if app.name == name
    ]

  # Safely get installed apps with manifest
  def get_installed_apps(self, raw: bool = False, both: bool = False) -> list:
    def safe_load(name):
      try:
        return load_app_manifest(self, name, raw=raw, both=both)
      except Exception:
        return None

    return [res for name in self.user.get_installed_apps() if (res := safe_load(name)) is not None]

  # Check if app is installed by name
  def is_app_installed(self, name: str) -> bool:
    return name in [manifest["name"] for manifest in self.get_installed_apps()]
  
  # Open app
  async def open_app(self, client_id: str, name: str, manifest, options) -> object:
    client = self.get_client(client_id)
    if client is None:
      raise Exception("Client not found")

    app = client.open_app(name, manifest, options)
    self.app_index[app.id] = client.id
    
    await self.events.emit_async("app:open", app.id, app.name)

    return app

  # Close app
  async def close_app(self, client: Client, app: App) -> None:
    await client.close_app(app)
    del self.app_index[app.id]

    await self.events.emit_async("app:close", app.id, app.name)
  
  # On app websocket data
  async def on_app_data(self, client: Client, app: App, data: dict) -> None:
    pass

  # On client websocket data
  async def on_client_data(self, client: Client, data: dict) -> None:
    pass

  # Handle client disconnection and clean up resources.
  async def on_client_close(self, client: Client) -> None:
    apps_list = [(app.id, app.name) for app in client.running_apps.values()]

    # closs on client
    await client.on_close()
    # delete in clients
    del self.clients[client.id]
    
    # Close all running_apps & remove
    for (app_id, name) in apps_list:
      self.app_index.pop(app_id, None)
      await self.events.emit_async("app:close", app_id, name)

    await self.events.emit_async("client:close", client.id)

  # On Start
  async def on_start(self, app: FastAPI) -> None:
    # Load services
    await self.services.load(self, app)

    # precheck setup apps, ui
    if not self.is_dev_mode:
      await setup_ui(self)
      await setup_apps(self)

    await self.events.emit_order("kikx:start", self)

  # On Stop
  async def on_close(self) -> None:
    # Close clients
    for client in list(self.clients.values()):
      await self.on_client_close(client)

    await self.services.on_close(self)
    await self.user.on_close(self)

    shutdown_file = self.config.resolve_path("storage://etc/shutdown.sh")
    if shutdown_file.is_file():
      sh(f"chmod +x {shutdown_file} && {shutdown_file}").run(False)

    await self.events.emit_order("kikx:close", self)

  # Force close client connection
  async def close_client(self, client: str) -> None:
    client = self.clients.get(client)
    if not client:
      raise Exception("Client not found")

    # close all apps and remove client
    await self.on_client_close(client)

  # Broadcast event to clients
  async def broadcast_to_clients(self, event: str, payload: dict) -> None:
    await asyncio.gather(
      *(client.send_event(event, payload) for client in self.clients.values()),
      return_exceptions=True
    )

  # Broadcast event to all apps or client apps
  async def broadcast_to_apps(self, event: str, payload: dict, client_id: str | None = None) -> None:
    if client_id is None:
      await asyncio.gather(
        *(client.broadcast_to_apps(event, payload) for client in self.clients.values()),
        return_exceptions=True
      )
      return

    client = self.get_client(client_id)
    if client is None:
      raise Exception("Client not found")
    
    await client.broadcast_to_apps(event, payload)

