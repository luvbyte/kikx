import asyncio
import logging
from uuid import uuid4
from pathlib import Path
from typing import Dict, Optional, List

from fastapi import WebSocket

from lib.utils import ensure_dir, dynamic_import
from core.models.app_models import AppModel
from core.func import FuncX, funcx, funcx_handler
from core.connection import Connection

logger = logging.getLogger(__name__)


class App(FuncX):
  def __init__(self, client_id: str, name: str, app_path: Path, config: AppModel, user: object):
    super().__init__()
    self.name: str = name
    self.id: str = uuid4().hex
    self.client_id: str = client_id
    self.app_path: Path = app_path
    self.config: AppModel = config
    self.title: str = config.title
    self.user = user  # Custom user object

    self.connection = Connection()
    self.__modules: List[Dict[str, object]] = []

    self.load_modules()

  @property
  def connected(self) -> bool:
    """Check if WebSocket is still connected."""
    return self.connection.is_connected

  def load_modules(self) -> None:
    """Dynamically load app modules from config."""
    modules_list = set(self.config.modules)
    for module_name in modules_list:
      try:
        module = dynamic_import(
          f"app_{module_name}",
          f"./core/apps/modules/{module_name}.py"
        )
        module_class = getattr(module, module_name.capitalize())
        module_obj = module_class(self)

        setattr(self, module_name, module_obj)
        self.__modules.append({
          "name": module_name,
          "module": module,
          "obj": module_obj
        })
        logger.info(f"Module loaded: {module_name}")
      except Exception as e:
        logger.exception(f"Failed to load module '{module_name}': {e}")

  def get_permissions(self, sub: Optional[str] = None) -> object:
    """Access permission config or subsection."""
    if sub is None:
      return self.config
    elif sub == "storage":
      return self.config.storage
    elif sub == "system":
      return self.config.system
    else:
      raise ValueError(f"Permissions: '{sub}' not found")

  def get_app_path(self) -> Path:
    return self.app_path

  def get_home_path(self) -> Path:
    return self.user.home_path

  def get_app_data_path(self) -> Path:
    """Return or create the app's data directory."""
    return ensure_dir(self.user.data_path / "data" / self.name)

  async def connect_websocket(self, websocket: WebSocket) -> None:
    """Bind a WebSocket connection to the app."""
    await self.connection.connect(websocket)
    logger.info(f"WebSocket connected for app: {self.name}")

  async def send_event(self, event: str, payload: object) -> None:
    """Send event to frontend."""
    await self.connection.send_event(event, payload)

  async def on_close(self) -> None:
    """Clean up all modules on app close."""
    results = await asyncio.gather(
      *[getattr(self, module["name"]).on_close() for module in self.__modules],
      return_exceptions=True
    )
    for module, result in zip(self.__modules, results):
      if isinstance(result, Exception):
        logger.warning(f"Error closing module {module['name']}: {result}")
    await super().on_close()

  def __str__(self) -> str:
    return f"{self.name} - {self.id}"
