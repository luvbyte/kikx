import os
from pathlib import Path
from typing import Any, Dict

from core.models.kikx_models import ServicesConfigModel
from lib.parser import parse_config
from lib.utils import import_relative_module, any_run

from core.logging import Logger

logging = Logger("kikx_services", "kikx_services.log")
logger = logging.get_logger()


class Service:
  def __init__(self, name: str, service_path: Path, core: Any):
    self.name = name
    self.path = service_path
    self.module = import_relative_module(f"services.{name}.main", f"kikx_service_{name}")

  async def on_start(self, core: Any) -> None:
    self.main._includes["core"] = core
    await self.main.on_start(core)
  
  async def on_close(self, core):
    await self.main.on_close(core)

  @property
  def main(self) -> Any:
    return getattr(self.module, "srv", None)

  @property
  def router(self) -> Any:
    return self.main.router

class Services:
  def __init__(self, services_config_path):
    self.config: ServicesConfigModel = parse_config(services_config_path, ServicesConfigModel)
    self.active_services: Dict[str, Service] = {}

  def get_enabled_services(self):
    return [name for name in os.listdir("services") if name not in self.config.disabled]

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
      
      logger.info(f"[+] Loaded Service: {name}")

  async def on_close(self, core) -> None:
    for name, service in self.active_services.items():
      await service.on_close(core)

    logger.info("All services closed.")
