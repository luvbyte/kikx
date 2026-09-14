import asyncio
import logging

from pathlib import Path
from typing import Any

from fastapi import WebSocket

from core.connection import Connection
from core.models.app import AppManifestModel, AppModel, AppOptionsModel

from lib.storage import KVStorage
from lib.utils import ensure_dir, generate_uuid, get_timestamp, joinpath


logger = logging.getLogger(__name__)


# ---------------------- App
class App:
  def __init__(
    self,
    client_id: str,
    name: str,
    app_path: Path,
    config: AppModel,
    user: Any,
    manifest: AppManifestModel,
    options: AppOptionsModel | dict,
  ) -> None:
    super().__init__()

    self.name: str = name
    self.id: str = generate_uuid()
    self.client_id: str = client_id
    self.app_path: Path = app_path
    self.config: AppModel = config
    self.manifest: AppManifestModel = manifest
    self.title: str = config.title
    self.user: Any = user

    # App start options
    self.options: AppOptionsModel = (
      options
      if isinstance(options, AppOptionsModel)
      else AppOptionsModel(**options)
    )
    self.sudo: bool = self.config.sudo or self.options.sudo

    # App opened time
    self.created_at: str = get_timestamp()

    # App WebSocket connection
    self.connection: Connection = Connection(
      "App",
      track_messages=self.config.connection.tracking,
    )

    # Loaded app modules
    self.__modules: list[dict[str, Any]] = []

    # Temporary KV storage
    self._data: KVStorage = KVStorage()

    logger.info(
      f"App Running ({self.name}) (ID: {self.id}) (Client: {self.client_id})"
    )

  # ---------------------- Info
  def info(self) -> dict[str, Any]:
    return {
      "id": self.id,
      "name": self.name,
      "title": self.title,
      "options": self.options.model_dump(),
      "manifest": self.manifest.model_dump(),
      "config": self.config.model_dump(),
      "sudo": self.is_sudo,
      "created_at": self.created_at,
      "connection": self.connection.info(),
    }

  @property
  def data(self) -> KVStorage:
    return self._data

  @property
  def connected(self) -> bool:
    return self.connection.is_connected

  @property
  def is_sudo(self) -> bool:
    return self.sudo

  # ---------------------- Config
  def save_config(self) -> None:
    logger.info(f"Saving app config: {self.name} (ID: {self.id})")
    self.user.save_app_config(self.name, self.config)

  # ---------------------- Paths
  def get_app_path(self) -> Path:
    return self.app_path

  def get_home_path(self) -> Path:
    return self.user.home_path

  def get_app_data_local_path(self) -> Path:
    return ensure_dir(joinpath(self.user.data_path / "data", self.name, "local"))

  def get_app_data_path(self) -> Path:
    return ensure_dir(joinpath(self.user.data_path / "data", self.name, "data"))

  def get_app_cache_path(self) -> Path:
    return ensure_dir(joinpath(self.user.data_path / "data", self.name, "cache"))

  # ---------------------- WebSocket
  async def connect_websocket(self, websocket: WebSocket) -> None:
    await self.connection.connect(websocket)
    logger.info(f"WebSocket connected for app: {self.name}")

  async def send_event(self, event: str, payload: Any) -> None:
    await self.connection.send_event(event, payload)

  # ---------------------- Close
  async def on_close(self) -> None:
    logger.info(f"App Closing ({self.name}) (ID: {self.id})")

    results = await asyncio.gather(
      *[
        getattr(self, module["name"]).on_close()
        for module in self.__modules
      ],
      return_exceptions=True,
    )

    for module, result in zip(self.__modules, results):
      if isinstance(result, Exception):
        logger.warning(
          f"Error closing module {module['name']}: {result}"
        )

    try:
      await asyncio.wait_for(self.connection.close(), timeout=2)
    except asyncio.TimeoutError:
      logger.warning("Timed out while closing connection from app.")

  def __str__(self) -> str:
    return f"App ({self.name}) - (ID: {self.id})"