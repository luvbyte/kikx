from fastapi import WebSocket

from starlette.websockets import WebSocketState

from importlib import import_module
from pathlib import Path
import importlib.util
import base64
import sys



# imports and saves module
def import_relative_module(path, name):
  return import_module(path, name)

def dynamic_import(module_name, file_path, cache = False):
  module = sys.modules.get(module_name)
  if module:
    # reload if needed
    return module
  
  # unsecure find usages
  file_path = Path(file_path).resolve()
  if not file_path.exists():
    raise FileNotFoundError(f"File '{file_path}' not found.")

  spec = importlib.util.spec_from_file_location(module_name, str(file_path))
  if spec and spec.loader:
    module = importlib.util.module_from_spec(spec)
    if cache:
      sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

  raise ImportError(f"Could not load module from '{file_path}'")

def is_websocket_connected(ws):
  if isinstance(ws, WebSocket):
    return ws.client_state != WebSocketState.DISCONNECTED

  return False


# converts utf-8 encoded to Base64
def convertToBase64(data):
  return base64.b64encode(data).decode("utf-8")

def ensure_dir(path):
  """Ensure the directory exists. If not, create it."""
  Path(path).mkdir(parents=True, exist_ok=True)
  return path