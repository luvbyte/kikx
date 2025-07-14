from fastapi import WebSocket
from starlette.websockets import WebSocketState

from importlib import import_module, util as importlib_util
from pathlib import Path
import base64
import sys


def import_relative_module(path: str, name: str):
  """
  Import a module relatively using the standard import mechanism.
  """
  return import_module(path, name)


def dynamic_import(module_name: str, file_path: str, cache: bool = False):
  """
  Dynamically import a module from a file path.

  Args:
    module_name: Name to assign to the module.
    file_path: Path to the Python file.
    cache: Whether to cache the module in sys.modules.

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
  Check if a WebSocket connection is still active.

  Args:
    ws: The WebSocket instance.

  Returns:
    True if connected, False otherwise.
  """
  return isinstance(ws, WebSocket) and ws.client_state != WebSocketState.DISCONNECTED


def convert_to_base64(data: bytes) -> str:
  """
  Convert bytes to a base64-encoded UTF-8 string.

  Args:
    data: Bytes to encode.

  Returns:
    Base64-encoded string.
  """
  return base64.b64encode(data).decode("utf-8")


def ensure_dir(path: str) -> str:
  """
  Ensure a directory exists; create it if it doesn't.

  Args:
    path: Path to the directory.

  Returns:
    The same path, for chaining if needed.
  """
  Path(path).mkdir(parents=True, exist_ok=True)
  return path
