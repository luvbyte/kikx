import sys
import base64
import inspect
import asyncio

from uuid import uuid4
from pathlib import Path
from importlib import import_module
from datetime import datetime, timezone
from importlib import util as importlib_util

from typing import Any, Callable, Union

from fastapi import WebSocket, HTTPException
from fastapi.responses import FileResponse

from starlette.websockets import WebSocketState

from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet, InvalidSpecifier



async def any_run(func, *args, **kwargs):
  if inspect.iscoroutinefunction(func):
    return await func(*args, **kwargs)
  else:
    return func(*args, **kwargs)

def get_timestamp():
  return datetime.now(timezone.utc).isoformat()

def generate_uuid() -> str:
  return uuid4().hex

def is_version_ok_deprecated(current_version: str, requirement: str) -> bool:
  try:
    version = Version(current_version)
    spec = SpecifierSet(requirement)
    return version in spec
  except (InvalidVersion, InvalidSpecifier):
    return False

def is_version_ok(current_version: str, requirement: str) -> bool:
  try:
    version = Version(current_version)
    
    # Allow patch updates
    if not any(requirement.strip().startswith(op) for op in "<>!=~="):
      requirement = f"~={requirement}"

    spec = SpecifierSet(requirement)
    return version in spec
  except (InvalidVersion, InvalidSpecifier):
    return False

def is_update_available(current_version: str, latest_version: str) -> bool:
  try:
    return Version(current_version) < Version(latest_version)
  except InvalidVersion:
    return False

def import_relative_module(path: str, name: str) -> Any:
  """
  Import a module relatively using standard import mechanisms.
  """
  return import_module(path, name)

def dynamic_import(module_name: str, file_path: str, cache: bool = False) -> Any:
  """
  Dynamically import a Python module from a file path.

  Args:
    module_name: The name to assign to the module.
    file_path: The file path of the module.
    cache: Whether to store it in sys.modules.

  Returns:
    The imported module object.
  """
  if module_name in sys.modules:
    return sys.modules[module_name]

  file_path = Path(file_path).resolve()
  if not file_path.is_file():
    raise FileNotFoundError(f"File '{file_path}' not found.")

  spec = importlib_util.spec_from_file_location(module_name, str(file_path))
  if not spec or not spec.loader:
    raise ImportError(f"Could not load module from '{file_path}'")

  module = importlib_util.module_from_spec(spec)
  if cache:
    sys.modules[module_name] = module

  spec.loader.exec_module(module)
  return module

def is_websocket_connected(ws: WebSocket) -> bool:
  """
  Check if a WebSocket connection is active.

  Args:
    ws: The WebSocket instance.

  Returns:
    True if connected, False otherwise.
  """
  return isinstance(ws, WebSocket) and ws.client_state == WebSocketState.CONNECTED

async def send_event(websocket: WebSocket, event: str, payload: Union[dict, Callable[[], dict]]) -> None:
  """
  Send a JSON event to a WebSocket client.

  Args:
    websocket: WebSocket connection.
    event: Event name string.
    payload: Dict or callable returning a dict.
  """
  if is_websocket_connected(websocket):
    try:
      await websocket.send_json({
        "event": event,
        "payload": payload() if callable(payload) else payload
      })
    except Exception:
      pass

def convert_to_base64(data: bytes) -> str:
  """
  Convert bytes to a base64-encoded string.

  Args:
    data: Byte data to encode.

  Returns:
    UTF-8 base64-encoded string.
  """
  return base64.b64encode(data).decode("utf-8")

def ensure_dir(path: str) -> str:
  """
  Ensure a directory exists; create it if missing.

  Args:
    path: Directory path.

  Returns:
    Same path.
  """
  Path(path).mkdir(parents=True, exist_ok=True)
  return path

def file_response(base: str | Path, *paths: str | Path) -> Path:
  """
  Safely join base with one or more path components.
  Returns a Path guaranteed to be inside base, or raises HTTPException(403/404).
  """
  base = Path(base).resolve()
  full_path = base.joinpath(*paths).resolve()

  # built-in safe check
  if not full_path.is_relative_to(base):
    raise HTTPException(status_code=403, detail="Forbidden path")
  
  if not full_path.is_file():
    raise HTTPException(status_code=404, detail="File not found")

  return FileResponse(full_path)

def joinpath(base: str | Path, *parts: str | Path) -> Path:
  base = Path(base).resolve()
  target = base.joinpath(*parts).resolve()

  if not target.is_relative_to(base):
    raise HTTPException(status_code=401, detail="Path traversal detected")

  return target
