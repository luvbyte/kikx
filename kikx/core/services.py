import os
import logging

from typing import Any
from pathlib import Path

from core.models.kikx_models import ServicesConfigModel

from lib.parser import parse_config
from lib.utils import import_relative_module



logger = logging.getLogger(__name__)


class Service:
  def __init__(self, name: str, service_path: Path, core: Any) -> None:
    self.name: str = name
    self.path: Path = service_path
    self.module = import_relative_module(f"services.{name}.main", f"kikx_service_{name}")
  
  def info(self) -> dict[str, Any]:
    return {
      "name": self.name,
      "path": f"{self.path}/{self.name}",
      "abs_path": self.main.path if self.main else None
    }

  async def on_start(self, core: Any) -> None:
    self.main._includes["core"] = core
    await self.main.on_start(core)

  async def on_close(self, core) -> None:
    await self.main.on_close(core)

  @property
  def main(self) -> Any:
    return getattr(self.module, "srv", None)

  @property
  def router(self) -> Any:
    return self.main.router

class Services:
  def __init__(self, services_config_path) -> None:
    self.config: ServicesConfigModel = parse_config(services_config_path, ServicesConfigModel)
    self.active_services: dict[str, Service] = {}

  def info(self) -> dict[str, Any]:
    return {
      "config": self.config.model_dump(),
      "active": { name: s.info() for name, s in self.active_services.items() }
    }

  def get_enabled_services(self) -> list[str]:
    return [name for name in os.listdir("services") if name not in self.config.disabled and not name.startswith("_")]

  async def load(self, core: Any, app: Any) -> None:
    for name in self.get_enabled_services():
      service_path = core.config.resolve_path("services")

      service = Service(name, service_path, core)
      app.include_router(
        service.router,
        prefix=f"/service/{name}",
        tags=[f"Service {name.capitalize()}"]
      )

      self.active_services[name] = service

      await service.on_start(core)

      core.scr.success(f"Loaded Service: {name}")

  async def on_close(self, core: Any) -> None:
    for name, service in self.active_services.items():
      await service.on_close(core)

    logger.info("All services closed.")
