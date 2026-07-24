import asyncio
import logging

from typing import Any
from pathlib import Path

from fastapi import WebSocket

from core.func import FuncX, funcx
from core.connection import Connection
from core.models.app_models import AppModel, AppOptionsModel, AppManifestModel

from lib.storage import KVStorage
from lib.utils import get_timestamp
from lib.utils import generate_uuid, ensure_dir, dynamic_import, joinpath



logger = logging.getLogger(__name__)


class App(FuncX):
  def __init__(
    self,
    client_id: str,
    name: str,
    app_path: Path,
    config: AppModel,
    user: Any,
    manifest: AppManifestModel,
    options: AppOptionsModel | dict
  ) -> None:

    super().__init__()

    self.name: str = name               # App unique name
    self.id: str = generate_uuid()      # App unique id
    self.client_id: str = client_id     # Client id which opened this app
    self.app_path: Path = app_path      # App path
    self.config: AppModel = config      # App config in data/
    self.manifest: AppManifestModel = manifest  # App manifest file app.json
    self.title: str = config.title      # App title
    self.user: Any = user                    # User instance
    
    # App Start options
    self.options: AppOptionsModel = options if isinstance(options, AppOptionsModel) else AppOptionsModel(**options)
    self.sudo: bool = True if self.config.sudo else self.options.sudo  # Sudo App

    # App opened time
    self.created_at: str = get_timestamp()
    # App ws connection
    self.connection: Connection = Connection("App", self.config.ws_tracking)
    # Loaded app modules
    self.__modules: list[dict[str, Any]] = []
    # Temp kv storage
    self._data: KVStorage = KVStorage()

    # Start loading app modules
    self.load_modules()

  def info(self) -> dict[str, Any]:
    """Get App info dict"""
    return {
      "id": self.id,
      "name": self.name,
      "title": self.title,

      "options": self.options.model_dump(),
      "manifest": self.manifest.model_dump(),
      "config": self.config.model_dump(),

      "sudo": self.is_sudo,
      "created_at": self.created_at,

      "connection": self.connection.info()
    }

  @property
  def data(self) -> KVStorage:
    return self._data

  @property
  def connected(self) -> bool:
    """Check if WebSocket is still connected."""
    return self.connection.is_connected

  @property
  def is_sudo(self) -> bool:
    return self.sudo

  # Saving app config
  def save_config(self) -> None:
    logger.info(f"Saving app config: {self.name} (ID: {self.id})")
    self.user.save_app_config(self.name, self.config)

  def load_modules(self) -> None:
    """Dynamically load app modules from config."""
    modules_list = self.config.modules.keys()
    for module_name in modules_list:
      try:
        module = dynamic_import(
          f"app_{module_name}",
          f"./core/apps/modules/{module_name}.py"
        )
        module_class = getattr(module, module_name.capitalize())
        module_obj = module_class(self, self.config.modules[module_name])

        setattr(self, module_name, module_obj)
        self.__modules.append({
          "name": module_name,
          "module": module,
          "obj": module_obj
        })
        logger.info(f"Module ({module_name}) loaded for {self}")
      except Exception as e:
        logger.exception(f"Failed to load module '{module_name}': {e}")

  def get_app_path(self) -> Path:
    return self.app_path

  def get_home_path(self) -> Path:
    return self.user.home_path

  def get_app_data_path(self) -> Path:
    """Return or create the app's data directory."""
    return ensure_dir(joinpath(self.user.data_path, "data", self.name))

  async def connect_websocket(self, websocket: WebSocket) -> None:
    """Bind a WebSocket connection to the app."""
    await self.connection.connect(websocket)
    logger.info(f"WebSocket connected for app: {self.name}")

  async def send_event(self, event: str, payload: Any) -> None:
    """Send event to frontend."""
    await self.connection.send_event(event, payload)

  async def on_close(self) -> None:
    """Clean up all modules on app close."""
    logger.info(f"Closing app: {self.name} (ID: {self.id})")
  
    await super().on_close()

    results = await asyncio.gather(
      *[getattr(self, module["name"]).on_close() for module in self.__modules],
      return_exceptions=True
    )
    for module, result in zip(self.__modules, results):
      if isinstance(result, Exception):
        logger.warning(f"Error closing module {module['name']}: {result}")
    
    # Try closing connection
    try:
      await asyncio.wait_for(self.connection.close(), timeout=2)
    except asyncio.TimeoutError:
      logger.warning("Timed out while closing connection from app.")


  def __str__(self) -> str:
    return f"App ({self.name}) - (ID: {self.id})"
