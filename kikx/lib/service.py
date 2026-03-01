from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from lib.event import Events
from lib.parser import parse_config

class KikxService:
  def __init__(self, file: str):
    self.path: Path = Path(file).parent
    self.name: str = self.path.name
    self.config: dict = {}
    self.router: APIRouter = APIRouter()
    self._includes: Dict[str, object] = {}
    self._include_routes: Dict[APIRouter, str] = {}
    self._events: Events = Events()
  
  async def on_start(self, core):
    await self._events.emit("startup", core)

  async def on_close(self, core):
    await self._events.emit("shutdown", core)

  # Include sub routes 
  def include(self, router: APIRouter, prefix: str, tags = []):
    router._srv = self

    self.router.include_router(
      router, prefix=prefix, tags=tags
    )
    self._include_routes[prefix] = router
    
    func = getattr(router, "on_router_init", None)
    try:
      if callable(func):
        func(self)
    except Exception:
      pass

  def get(self, name: str) -> Optional[object]:
    return self._includes.get(name)

  def exception(self, status_code: int = 404, detail: str = "") -> None:
    raise HTTPException(status_code=status_code, detail=str(detail))

  def get_core(self) -> object:
    core = self.get("core")
    if core is None:
      self.exception(500, "Service error: Core service not available")
    return core

  def get_client(self, request: Request) -> object:
    client_id = request.headers.get("kikx-client-id")
    if client_id is None:
      self.exception(401, "Missing 'kikx-client-id' header")
    core = self.get_core()
    client = core.get_client(client_id)
    if client is None:
      self.exception(404, "Client not found")
    return client

  def get_client_app(self, request: Request) -> Tuple[object, object]:
    app_id = request.headers.get("kikx-app-id")
    if app_id is None:
      self.exception(401, "Missing 'kikx-app-id' header")
    core = self.get_core()
    client, app = core.get_client_app_by_id(app_id)
    if client is None or app is None:
      self.exception(404, "Client or app not found")

    return client, app

  def get_client_or_app(self, request: Request) -> Tuple[object, Optional[object]]:
    if "kikx-client-id" in request.headers:
      return self.get_client(request), None
    elif "kikx-app-id" in request.headers:
      return self.get_client_app(request)
    self.exception(401, "Require 'kikx-[app|client]-id' in headers")

  def on(self, event: str) -> Callable:
    def wrapper(func: Callable) -> None:
      self._events.add_event(event, func)
    return wrapper

  # --
  async def broadcast_signal_to_clients(self, signal: str, payload: dict) -> None:
    core = self.get_core()
    payload = { "signal": signal, "payload": payload }
    
    await core.broadcast_client_event("signal", payload)
  
  # broadcast to all running apps - for all clients / client
  async def broadcast_signal_to_apps(self, signal: str, payload: dict, client_id: str | None = None) -> None:
    core = self.get_core()
    payload = { "signal": signal, "payload": payload }

    await core.broadcast_app_event("signal", payload, client_id)


def create_service(file: str) -> KikxService:
  return KikxService(file)

