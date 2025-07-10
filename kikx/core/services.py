from core.errors import raise_error
from lib.utils import import_relative_module
from lib.parser import parse_config
from fastapi import Depends
from core.config.models import ServicesModel

class Service:
  def __init__(self, name, service_path, main, core):
    self.name = name
    self.path = service_path
    self._main = main # entry object
    # self.module = dynamic_import("service_" + name, service_path / "main.py")
    self.module = import_relative_module(f"{self.path}.{name}.main", "service_" + name)
    
    self.init(core)
  
  def emit(self, event, *args, **kwargs):
    self.main._events.emit(event, *args, **kwargs)

  def init(self, core):
    self.main._includes["core"] = core
    self.emit("load")
  
  @property
  def main(self):
    return getattr(self.module, self._main, None)

  @property
  def router(self):
    return self.main

class K1Service(Service):
  @property
  def router(self):
    return self.main.router

class K2Service(Service):
  pass


class Services:
  def __init__(self, services_config_path):
    # services {}
    self.manifest = parse_config(services_config_path, ServicesModel)
    self.active_services = {}
    
  def is_service_enabled(self, name):
    return name in self.manifest.enabled
  
  def get_enabled_services(self):
    return list(dict.fromkeys(self.manifest.enabled))

  def load(self, core, app):
    # loading
    for name in self.get_enabled_services():
      service_config = self.manifest.installed.get(name)
      if service_config is None:
        print(f"Service Config: {name} not found skipping...")
        continue
      
      # fastapi router service
      if service_config.type == "k1":
        service = K1Service(name, core.config.resolve_path("services"), service_config.main, core)
        app.include_router(
          service.router, 
          prefix=f"/service/{name}",
          tags=["Service " + name.capitalize()],
          dependencies=[Depends(core.on_service_request)]
        )
      elif service_config.type == "k2":
        service = K2Service(name, core.config.resolve_path("services"), service_config.main, core)

      self.active_services[name] = service
      print(f"[+] Service( {service_config.type} ) : {name}")

  # emiting close event
  def on_close(self):
    for name, service in self.active_services.items():
      service.emit("close")
