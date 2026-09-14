import json
from pathlib import Path
from fastapi import WebSocket

from core.storage import Storage

from .kikx import KikxServer

from lib.parser import ParseConfig

from core.models.kikx import KikxConfigModel
from core.models.manager import MANAGER_KIKX_SCHEMA


class KikxManagerConfig:
  def __init__(self, storage: str):
    self.storage = Storage(storage)

    self.kikx_config_path: Path = self.storage.join("config/kikx.json")
    self.kikx_config: ParseConfig = ParseConfig(self.kikx_config_path, KikxConfigModel, lorc=True)

class KikxManagerCore:
  def __init__(self, storage):
    self.config = KikxManagerConfig(storage)
    self.kikx_server = KikxServer(self.config)
    
    self.clients: list[WebSocket] = []

    # Stdout
    self.kikx_server.events.add_event("stdout", self.on_kikx_stdout)

  async def broadcast(self, event: str, payload: dict) -> None:
    for client in self.clients:
      await client.send_json({ "event": event, "payload": payload })

  async def on_kikx_stdout(self, message: str) -> None:
    await self.broadcast("kikx:stdout", { "message": message })

  def get_status(self) -> dict:
    return {
      "kikx": self.kikx_server.get_status()
    }
  
  def get_settings(self, reset: bool = False) -> dict:
    if reset:
      self.config.kikx_config.set_default_config()
    
    return {
      "schema": MANAGER_KIKX_SCHEMA,
      "config": self.config.kikx_config.data_obj
    }

  def update_settings(self, settings):
    current = self.config.kikx_config.data

    for field in settings.model_fields_set:
      setattr(current, field, getattr(settings, field))

    self.config.kikx_config.save()

  async def start_kikx_server(self) -> None:
    await self.kikx_server.start()

  async def stop_kikx_server(self) -> None:
    await self.kikx_server.stop()
  
  def get_kikx_stdout(self) -> list[str]:
    return self.kikx_server.get_stdout()

  async def on_close(self) -> None:
    await self.kikx_server.on_close()

