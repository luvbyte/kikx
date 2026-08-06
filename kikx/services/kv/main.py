import json
import logging

from fastapi import Request, Depends

from typing import Any
from pathlib import Path
from pydantic import BaseModel

from lib.service import create_service
from lib.utils import generate_uuid, ensure_dir



logger = logging.getLogger(__name__)


srv = create_service(__file__, desc="App key value service")


def check_permisson(request: Request):
  core = srv.get_core()

  _, app = srv.get_client_app(request)

  # If app - check kv exists in app config
  if not app.config.kv:
    srv.exception(403, "Require 'kv' permission")

  return core


class Collection:
  def __init__(self, app_name: str, app_id: str, dfile_path: Path):
    self.id: str = generate_uuid()
    self.app_name: str = app_name
    self.app_id: str = app_id

    self.dfile_path: Path = dfile_path
    # object of k: v / {}
    self._kv: dict = self.load(self.dfile_path)
  
    self.__closed: bool = False

  # Load dfile
  def load(self, dfile: Path) -> dict:
    default = {}
    
    if not dfile.is_file():
      return default
    try:
      with open(self.dfile_path, "r") as file:
        return json.load(file)
    except Exception:
      return default

  # Save dfile
  def save(self) -> None:
    try:
      with open(self.dfile_path, "w") as file:
        json.dump(self._kv, file)
    except Exception as e:
      logger.exception(f"Service(KV) Error saving datafile: {e}")
  
  # Reset
  def reset(self) -> bool:
    self._kv = {}
    self.save()
    
    return True

  # Get key or fallback (None)
  def get(self, key: str, fallback: Any | None = None) -> Any | None:
    return self._kv.get(key, fallback)

  # Set key
  def set(self, key: str, value: Any) -> None:
    self._kv[key] = value
  
  # Get or set key: value
  def get_or_set(self, key: str, value: Any) -> Any:
    if not self.has(key):
      self.set(key, value)

    return self.get(key)
  
  # Check if has key
  def has(self, key) -> bool:
    return key in self._kv
  
  # Remove key
  def pop(self, key) -> Any:
    if not self.has(key):
      raise KeyError("Key not found")
    return self._kv.pop(key)

  # Config collection
  def config(self, command: str) -> None:
    pass

  def info(self) -> dict:
    return {
      "dfile_path": str(self.dfile_path),
      "length": len(self._kv.keys())
    }
  
  def _close(self) -> None:
    self.save()

  def close(self) -> None:
    if self.__closed:
      return
    self._close()
    self.__closed = True

class KVM:
  def __init__(self) -> None:
    # AppName: Collection
    self._collections: dict[str, Collection] = {}
  
  def get_collection(self, core: Any, app: Any) -> Collection:
    collection = self._collections.get(app.name, None)
    if collection is not None:
      return collection

    dfile_path = (ensure_dir(app.get_app_data_path() / ".__kv") / "data.json").resolve()
    collection = self._collections[app.name] = Collection(app.name, app.id, dfile_path)

    logger.info(f"KV: Collection init by App: {app.name} ID: {app.id}, C: {self._collections}")

    return collection

  # --------------- LIFECYCLE
  async def on_close_app(self, app_id: str, app_name: str) -> None:
    core = srv.get_core()

    if app_name not in self._collections:
      return

    if len(core.get_apps_by_name(app_name)) <= 0:
      self._collections.pop(app_name).close()
      logger.info(f"KV: Collection closed for {app_name}")

  def on_shutdown(self) -> None:
    for c in self._collections.values():
      c.close()
    
    logger.info("Service(KV) Collections Closed.")

kvm = KVM()

@srv.on("startup")
def startup(core: Any) -> None:
  core.events.add_event("app:close", kvm.on_close_app)

@srv.on("shutdown")
def shutdown(core: Any) -> None:
  kvm.on_shutdown()

class SetCollectionModel(BaseModel):
  key: str
  value: Any

# Info
@srv.router.get("/info")
async def info(request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)
  
  return kvm.get_collection(core, app).info()

# Get Value by key
@srv.router.get("/get")
async def get(key: str, request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)

  c = kvm.get_collection(core, app)
  exists = c.has(key)
  value = c.get(key) if exists else None

  return {
    "key": key,
    "exists": exists,
    "value": value
  }

# Set key, value
@srv.router.post("/set")
def set(payload: SetCollectionModel, request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)

  kvm.get_collection(core, app).set(payload.key, payload.value)

  return { "key": payload.key, "value": payload.value }

# If Check if exists
@srv.router.get("/exists")
async def exists(key: str, request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)

  return kvm.get_collection(core, app).has(key)

# Get or set
@srv.router.post("/get-set")
async def get_or_set(payload: SetCollectionModel, request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)

  return kvm.get_collection(core, app).get_or_set(payload.key, payload.value)

# Pop / Delete
@srv.router.get("/pop")
async def pop_key(key: str, request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)
  
  try:
    return kvm.get_collection(core, app).pop(key)
  except Exception:
    srv.exception(404, "Key not found")

# Save
@srv.router.post("/save")
async def save_collection(request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)
  
  return kvm.get_collection(core, app).save()

# Reset
@srv.router.post("/reset")
async def reset_collection(request: Request, core = Depends(check_permisson)):
  _, app = srv.get_client_app(request)
  
  return kvm.get_collection(core, app).reset()

@srv.router.get("/config")
async def config(command: str, request: Request, core = Depends(check_permisson)):
  pass
