from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from lib.parser import parse_config


class Events:
  def __init__(self):
    self.__events: Dict[str, List[Callable]] = {}

  def add_event(self, event: str, func: Callable) -> None:
    if event not in self.__events:
      self.__events[event] = []
    self.__events[event].append(func)

  def emit(self, event: str, *args, **kwargs) -> None:
    for func in self.__events.get(event, []):
      func(*args, **kwargs)


class KikxService:
  def __init__(self, file: str):
    self.path: Path = Path(file).parent
    self.name: str = self.path.name
    self.config: dict = {}
    self.router: APIRouter = APIRouter()
    self._includes: Dict[str, object] = {}
    self._events: Events = Events()

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
      self.exception(400, "Missing 'kikx-client-id' header")
    core = self.get_core()
    client = core.get_client(client_id)
    if client is None:
      self.exception(400, "Unauthorized client")
    return client

  def get_client_app(self, request: Request) -> Tuple[object, object]:
    app_id = request.headers.get("kikx-app-id")
    if app_id is None:
      self.exception(400, "Missing 'kikx-app-id' header")
    core = self.get_core()
    client, app = core.get_client_app_by_id(app_id)
    if client is None or app is None:
      self.exception(401, "Unauthorized client or app")
    if self.name not in app.config.services:
      self.exception(401, f"Service '{self.name}' not found in app permissions")
    return client, app

  def get_client_or_app(self, request: Request) -> Tuple[object, Optional[object]]:
    if "kikx-client-id" in request.headers:
      return self.get_client(request), None
    elif "kikx-app-id" in request.headers:
      return self.get_client_app(request)
    self.exception(400, "Unauthorized: Missing 'kikx-[app|client]-id' in headers")

  def on(self, event: str) -> Callable:
    def wrapper(func: Callable) -> None:
      self._events.add_event(event, func)
    return wrapper


def create_service(file: str) -> KikxService:
  return KikxService(file)

