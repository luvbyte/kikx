import sys
import asyncio
import subprocess
from typing import Dict, Optional, Tuple, Union

from core.auth import Auth
from core.client import Client
from core.config import Config
from core.services import Services
from core.console import Console
from core.user import User

from core.setup import pre_check_apps

from lib.event import Events
from core import __version__, __author__


from core.logging import Logger

logging = Logger("kikx_core", "kikx_core.log")
logger = logging.get_logger()

# -------------------------------------
# Core API
# -------------------------------------


class Core:
  def __init__(self, storage_path: str, dev_mode: bool = False):
    """Initialize the core system: config, plugins, services, auth, users, etc."""
    # Dev mode
    self._dev_mode = dev_mode

    # Load configuration
    self.config = Config(storage_path)

    # Run boot script if it exists
    boot_file = self.config.resolve_path("storage://etc/boot.sh")
    if boot_file.exists() and not boot_file.is_dir():
      subprocess.Popen(
        f"chmod +x {boot_file} && {boot_file}",
        shell=True,
        stdout=sys.stdout,
        stdin=sys.stdin,
        stderr=sys.stderr
      ).wait()

    # Initialize subsystems
    self.services = Services(self.config.resolve_path("storage://config/services.json"))
    self.auth = Auth(self.config.resolve_path("storage://config/auth.json"))

    self.user = User(
      self.auth.user_config,
      self.config.resolve_path("data://"),
      self.config.resolve_path("home://"),
      self.config.resolve_path("storage://")
    )

    self.clients: Dict[str, Client] = {}
    self.app_index: Dict[str, str] = {}  # Maps app_id -> client_id
    
    self.events = Events()
    self.scr = Console()
  
  @property
  def version(self):
    return __version__
  
  @property
  def author(self):
    return __author__
  
  @property
  def is_dev_mode(self):
    return self._dev_mode

  def get_client(self, client_id: str) -> Optional[Client]:
    """Return a client by ID."""
    return self.clients.get(client_id)

  def get_ui_config(self, name: str):
    try:
      return self.config.kikx.ui[name]
    except ValueError:
      raise ValueError(f"UI '{name}' not found in kikx config")

  def get_client_app_by_id(self, app_id: str) -> Tuple[Optional[Client], Optional[object]]:
    """
    Return the (client, app) tuple given an app ID.
    Returns (None, None) if not found or invalid.
    """
    client_id = self.app_index.get(app_id)
    if client_id is None:
      return None, None

    client = self.clients.get(client_id)
    if client is None:
      return None, None

    app = client.running_apps.get(app_id)
    return (client, app) if app else (None, None)
  
  # --------------------------- Apps
  async def open_app(self, client_id: str, name: str, manifest, sudo) -> object:
    """
    Open an app for a given client.
    Raises an error if the client does not exist.
    """
    client = self.clients.get(client_id)
    if client is None:
      raise Exception("client not found")

    app = client.open_app(name, manifest, sudo)
    self.app_index[app.id] = client.id
    
    await self.events.emit_async("app:open", app.id)

    return app

  async def close_app(self, client: Client, app: object) -> None:
    """
    Close an app and remove it from the app index.
    """
    await client.close_app(app)
    del self.app_index[app.id]
    
    await self.events.emit_async("app:close", app.id)

  async def on_app_data(self, client: Client, app: object, data: dict) -> None:
    """Handle data received from the app (placeholder)."""
    event = data.get("event")
    if event == "ping":
      await app.connection.send_event("pong", data.get("payload", {}))

  async def on_client_data(self, client: object, data: dict) -> None:
    """Handle data received from the client (placeholder)."""
    event = data.get("event")
    if event == "ping":
      await client.connection.send_event("pong", {})

  async def on_app_disconnect(self, client: Client, app: object) -> None:
    """Handle app disconnect event (placeholder)."""
    await self.events.emit_async("app:disconnect", app.id)

  # --------------------------- Client
  async def on_client_disconnect(self, client: Client) -> None:
    """Handle client disconnection and clean up resources."""
    # Close all running_apps & remove
    for app_id in list(client.running_apps.keys()):
      self.app_index.pop(app_id, None)

    # closs on client
    await client.on_close()
    # delete in clients
    del self.clients[client.id]

    await self.events.emit_async("client:disconnect", client.id)

  # On startup / load services, plugins
  async def on_start(self, app) -> None:
    await self.services.load(self, app)

    # precheck built in apps
    if not self.is_dev_mode:
      await pre_check_apps(self)

    await self.events.emit_order("kikx:start", self)

  # On shutdown /
  async def on_close(self) -> None:
    for client in list(self.clients.values()):
      await self.on_client_disconnect(client)

    await self.services.on_close(self)
    await self.user.on_close(self)

    shutdown_file = self.config.resolve_path("storage://etc/shutdown.sh")
    if shutdown_file.exists() and not shutdown_file.is_dir():
      subprocess.Popen(
        f"chmod +x {shutdown_file} && {shutdown_file}",
        shell=True,
        stdout=sys.stdout,
        stdin=sys.stdin,
        stderr=sys.stderr
      ).wait()
    
    await self.events.emit_order("kikx:close", self)

  # Force close client connection
  async def close_client(self, client: str):
    client = self.clients.get(client)
    if not client:
      raise Exception("Session not found")

    # close all apps and remove client
    await self.on_client_disconnect(client)

    await self.events.emit_async("client:closed", client.id)

    return True
  
  # Broadcast event to clients
  async def broadcast_to_clients(self, event, payload):
    await asyncio.gather(
      *(client.send_event(event, payload) for client in self.clients.values()),
      return_exceptions=True
    )

  # Broadcast event to apps / client - apps
  async def broadcast_to_apps(self, event, payload, client_id = None):
    if client_id is None:
      await asyncio.gather(
        *(client.broadcast_to_apps(event, payload) for client in self.clients.values()),
        return_exceptions=True
      )
      return None

    client = self.get_client(client_id)
    if client is None:
      raise Exception("Client not found")
    
    await client.broadcast_to_apps(event, payload)

