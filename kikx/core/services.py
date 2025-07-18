import logging
from pathlib import Path
from typing import Any, Dict

from core.errors import raise_error
from core.models.kikx_models import ServicesModel
from lib.parser import parse_config
from lib.utils import import_relative_module

logger = logging.getLogger(__name__)


class Service:
  """Base class representing a generic service module."""
  def __init__(self, name: str, service_path: Path, main: str, core: Any):
    self.name = name
    self.path = service_path
    self._main = main  # entry class/function name in service main.py
    self.module = import_relative_module(f"{self.path}.{name}.main", f"service_{name}")
    self.init(core)

  def emit(self, event: str, *args, **kwargs) -> None:
    """Emit lifecycle event to the service."""
    self.main._events.emit(event, *args, **kwargs)

  def init(self, core: Any) -> None:
    """Initialize service with core dependencies."""
    self.main._includes["core"] = core
    self.emit("load")

  @property
  def main(self) -> Any:
    """Return main entry point object (usually a class instance)."""
    return getattr(self.module, self._main, None)

  @property
  def router(self) -> Any:
    """Return router if present (default is main itself)."""
    return self.main


class K1Service(Service):
  """FastAPI-compatible service exposing a router."""
  @property
  def router(self) -> Any:
    return self.main.router


class K2Service(Service):
  """Generic service without explicit router (background, scheduled, etc.)."""
  pass


class Services:
  """Manages the lifecycle of all services from the configuration."""
  def __init__(self, services_config_path: Path):
    self.manifest: ServicesModel = parse_config(services_config_path, ServicesModel)
    self.active_services: Dict[str, Service] = {}

  def is_service_enabled(self, name: str) -> bool:
    """Check if a service is enabled."""
    return name in self.manifest.enabled

  def get_enabled_services(self) -> list[str]:
    """Return a deduplicated list of enabled services."""
    return list(dict.fromkeys(self.manifest.enabled))

  def load(self, core: Any, app: Any) -> None:
    """Load all enabled services and attach routers if needed."""
    for name in self.get_enabled_services():
      service_config = self.manifest.installed.get(name)
      if service_config is None:
        logger.warning(f"Service config for '{name}' not found, skipping...")
        continue

      service_path = core.config.resolve_path("services")

      if service_config.type == "k1":
        service = K1Service(name, service_path, service_config.main, core)
        app.include_router(
          service.router,
          prefix=f"/service/{name}",
          tags=[f"Service {name.capitalize()}"]
        )
      elif service_config.type == "k2":
        service = K2Service(name, service_path, service_config.main, core)
      else:
        logger.warning(f"Unknown service type '{service_config.type}' for '{name}', skipping...")
        continue

      self.active_services[name] = service
      logger.info(f"[+] Loaded Service ({service_config.type}): {name} => {service_config.title}")

  def on_close(self) -> None:
    """Emit close event to all loaded services."""
    for name, service in self.active_services.items():
      service.emit("close")
    logger.info("All services closed.")
