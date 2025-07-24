import subprocess
import sys
from typing import Dict, Optional, Tuple

from core.auth import Auth
from core.client import Client
from core.config import Config
from core.errors import raise_error
from core.plugins import PluginsManager
from core.services import Services
from core.shortlink import ShortLink
from core.user import User


# -------------------------------------
# Core API
# -------------------------------------

class Core:
  def __init__(self):
    """Initialize the core system: config, plugins, services, auth, users, etc."""
    # Load configuration
    self.config = Config("../storage")

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
    self.plugins = PluginsManager(self.config.kikx.plugins)
    self.services = Services(self.config.resolve_path("storage://config/services.json"))
    self.auth = Auth(self.config.resolve_path("storage://config/auth.json"))

    self.user = User(
      self.auth.user_config,
      self.config.resolve_path("data://"),
      self.config.resolve_path("home://"),
      self.config.resolve_path("storage://")
    )

    self.shortlink = ShortLink(self.config.resolve_path("storage://shortlinks"))

    self.clients: Dict[str, Client] = {}
    self.app_index: Dict[str, str] = {}  # Maps app_id -> client_id

  def get_client(self, client_id: str) -> Optional[Client]:
    """Return a client by ID."""
    return self.clients.get(client_id)

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

  def open_app(self, client_id: str, name: str) -> object:
    """
    Open an app for a given client.
    Raises an error if the client does not exist.
    """
    client = self.clients.get(client_id)
    if client is None:
      raise_error("client not found")

    app = client.open_app(name)
    self.app_index[app.id] = client.id
    return app

  async def close_app(self, client: Client, app: object) -> None:
    """
    Close an app and remove it from the app index.
    """
    await client.close_app(app)
    del self.app_index[app.id]
    print("App Index", self.app_index)

  async def on_app_data(client: Client, app: object, data: dict) -> None:
    """Handle data received from the app (placeholder)."""
    pass

  async def on_client_data(self, client: Client, app: object, data: dict) -> None:
    """Handle data received from the client (placeholder)."""
    pass

  async def on_app_disconnect(self, client: Client, app: object) -> None:
    """Handle app disconnect event (placeholder)."""
    pass
  
  # --------------------------- Client
  async def on_client_disconnect(self, client: Client) -> None:
    """Handle client disconnection and clean up resources."""
    for app_id in list(client.running_apps.keys()):
      self.app_index.pop(app_id, None)

    await client.on_close()
    del self.clients[client.id]

  async def on_start(self) -> None:
    """Called before FastAPI starts (placeholder)."""
    pass

  async def on_close(self) -> None:
    """Called before FastAPI shuts down for cleanup."""
    self.plugins.shutdown()
    self.services.on_close()
    self.user.on_close()

    shutdown_file = self.config.resolve_path("storage://etc/shutdown.sh")
    if shutdown_file.exists() and not shutdown_file.is_dir():
      subprocess.Popen(
        f"chmod +x {shutdown_file} && {shutdown_file}",
        shell=True,
        stdout=sys.stdout,
        stdin=sys.stdin,
        stderr=sys.stderr
      ).wait()
