from pathlib import Path
from typing import Callable, Any

from fastapi import APIRouter, HTTPException, Request

from lib.event import Events


# ---------------------- Kikx Service

class KikxService:
  def __init__(self, file: str, desc: str | None = None) -> None:
    # Service abs path
    self.path: Path = Path(file).parent

    # Meta
    self.name: str = self.path.name
    self.desc: str | None = desc
    self.config: dict = {}

    # Fastapi Router
    self.router: APIRouter = APIRouter()

    # Dict set by Service
    self._includes: dict[str, Any] = {}

    # Sub routes
    self._include_routes: dict[APIRouter, str] = {}

    # Service events
    self._events: Events = Events()

    # Health API route
    self.router.add_api_route("/health", lambda: self.ok())

  # Service start
  async def on_start(self, core: Any) -> None:
    await self._events.emit("startup", core, ignore_errors=False)

  # Service close
  async def on_close(self, core: Any) -> None:
    await self._events.emit("shutdown", core, ignore_errors=False)

  # Include sub routes
  def include(self, router: APIRouter, prefix: str, tags: list[str] | None = None) -> None:
    router._srv = self

    self.router.include_router(router, prefix=prefix, tags=tags or [])
    self._include_routes[prefix] = router

    func = getattr(router, "on_router_init", None)
    if callable(func):
      func(self)

  # Get from includes
  def get(self, name: str) -> Any | None:
    return self._includes.get(name, None)

  # Raise HTTPException with status_code, detail
  def exception(self, status_code: int = 500, exception: str = "Unknown Error") -> None:
    if isinstance(exception, HTTPException):
      raise exception

    raise HTTPException(status_code=status_code, detail=str(exception))

  def ok(self, message: str = "success"):
    return {"message": message}

  # Get core instance
  def get_core(self) -> Any:
    core = self.get("core")

    if core is None:
      self.exception(500, "Service error: Core service not available")

    return core

  # Get client from request
  def get_client(self, request: Request) -> Any:
    client_id = request.headers.get("kikx-client-id")

    if client_id is None:
      self.exception(401, "Missing 'kikx-client-id' header")

    core = self.get_core()
    client = core.get_client(client_id)

    if client is None:
      self.exception(404, "Client not found")

    return client

  # Get app + client from request
  def get_client_app(self, request: Request) -> tuple[Any, Any]:
    app_id = request.headers.get("kikx-app-id")

    if app_id is None:
      self.exception(401, "Missing 'kikx-app-id' header")

    core = self.get_core()
    client, app = core.get_client_app_by_id(app_id)

    if client is None or app is None:
      self.exception(404, "Client or app not found")

    return client, app

  # Get client / app from request
  # Client: (client, None) | App: (client, app)
  def get_client_or_app(self, request: Request) -> tuple[Any, Any | None]:
    if "kikx-client-id" in request.headers:
      return self.get_client(request), None

    if "kikx-app-id" in request.headers:
      return self.get_client_app(request)

    self.exception(401, "Require 'kikx-[app|client]-id' in headers")

  # Add service event handler
  def add_event(self, event, func):
    self._events.add_event(event, func)

  # Add service event handler
  def on(self, event: str) -> Callable:
    def wrapper(func: Callable) -> None:
      self.add_event(event, func)

    return wrapper


# ---------------------- Create service instance

def create_service(file: str, *args, **kwargs) -> KikxService:
  return KikxService(file, *args, **kwargs)