import asyncio
from pathlib import Path
from typing import Dict, Optional, List

from fastapi import WebSocket

from lib.utils import get_timestamp

from lib.utils import generate_uuid, ensure_dir, dynamic_import, joinpath
from core.models.app_models import AppModel
from core.func import FuncX, funcx, funcx_handler
from core.connection import Connection

from core.logging import Logger


logging = Logger("kikx_apps", "kikx_apps.log")
logger = logging.get_logger()



class App(FuncX):
  def __init__(self, client_id: str, name: str, app_path: Path, config: AppModel, user: object, manifest, sudo=False):
    super().__init__()
    self.name: str = name
    self.id: str = generate_uuid()
    self.client_id: str = client_id
    self.app_path: Path = app_path
    self.config: AppModel = config
    self.manifest = manifest
    self.title: str = config.title
    self.user = user  # Custom user object
    
    self.sudo = True if self.config.sudo else sudo  # Sudo App
    
    self.created_at = get_timestamp()

    self.connection = Connection()
    self.__modules: List[Dict[str, object]] = []

    self.load_modules()

  def info(self):
    return {
      "id": self.id,
      "name": self.name,
      "title": self.title,
      
      "sudo": self.sudo,
      "created_at": self.created_at,

      "connection": self.connection.info()
    }

  @property
  def connected(self) -> bool:
    """Check if WebSocket is still connected."""
    return self.connection.is_connected

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

  async def send_event(self, event: str, payload: object) -> None:
    """Send event to frontend."""
    await self.connection.send_event(event, payload)

  async def on_close(self) -> None:
    """Clean up all modules on app close."""
    logger.info(f"Closing app: {self.name} (ID: {self.id})")

    results = await asyncio.gather(
      *[getattr(self, module["name"]).on_close() for module in self.__modules],
      return_exceptions=True
    )
    for module, result in zip(self.__modules, results):
      if isinstance(result, Exception):
        logger.warning(f"Error closing module {module['name']}: {result}")
    await super().on_close()

  def __str__(self) -> str:
    return f"App ({self.name}) - (ID: {self.id})"
