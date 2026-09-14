import asyncio
import json
import logging
import threading

from fastapi import Request, Depends
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lib.service import create_service
from lib.utils import generate_uuid, ensure_dir


logger = logging.getLogger(__name__)


srv = create_service(__file__, desc="App key value service")


# --------------- Models

class SetCollectionModel(BaseModel):
  key: str
  value: Any

# --------------- Depends

def get_app(request: Request):
  _, app = srv.get_client_app(request)
  return app

def check_permisson(request: Request):
  core = srv.get_core()
  app = get_app(request)

  if not app.config.has_service("kv"):
    srv.exception(403, "Service 'kv' not found in config")

  return core

# --------------- Collection

class Collection:
  def __init__(self, app_name: str, app_id: str, dfile_path: Path):
    self.id: str = generate_uuid()
    self.app_name: str = app_name
    self.app_id: str = app_id
    self.dfile_path: Path = dfile_path

    self._lock = threading.RLock()
    self.__closed = False

    self._kv: dict[str, Any] = self.load(self.dfile_path)

  # --------------- Internal

  def _ensure_open(self) -> None:
    if self.__closed:
      raise RuntimeError("Collection is closed")

  # --------------- Load

  def load(self, dfile: Path) -> dict[str, Any]:
    if not dfile.is_file():
      return {}

    try:
      with dfile.open("r", encoding="utf-8") as file:
        data = json.load(file)

      if not isinstance(data, dict):
        logger.error(
          "Service(KV): invalid data format in %s; expected object",
          dfile,
        )
        return {}

      return data

    except json.JSONDecodeError:
      logger.exception(
        "Service(KV): invalid JSON datafile: %s",
        dfile,
      )
      return {}

    except OSError:
      logger.exception(
        "Service(KV): error reading datafile: %s",
        dfile,
      )
      return {}

  # --------------- Save

  def save(self) -> bool:
    with self._lock:
      self._ensure_open()

      # Take a snapshot while holding the lock.
      data = dict(self._kv)

      tmp_path = self.dfile_path.with_suffix(".tmp")

      try:
        self.dfile_path.parent.mkdir(parents=True, exist_ok=True)

        with tmp_path.open("w", encoding="utf-8") as file:
          json.dump(
            data,
            file,
            ensure_ascii=False,
            separators=(",", ":"),
          )
          file.flush()

        # Atomic replacement.
        tmp_path.replace(self.dfile_path)

        return True

      except (OSError, TypeError, ValueError):
        logger.exception(
          "Service(KV): error saving datafile: %s",
          self.dfile_path,
        )

        try:
          tmp_path.unlink(missing_ok=True)
        except OSError:
          pass

        return False

  # --------------- Reset

  def reset(self) -> bool:
    with self._lock:
      self._ensure_open()

      old_kv = self._kv
      self._kv = {}

      if self.save():
        return True

      # Restore in-memory state if persistence failed.
      self._kv = old_kv
      return False

  # --------------- Get

  def get(
    self,
    key: str,
    fallback: Any | None = None,
  ) -> Any | None:
    with self._lock:
      self._ensure_open()
      return self._kv.get(key, fallback)
  
  # --------------- Dump
  
  def dump(self) -> dict[str, Any]:
    with self._lock:
      self._ensure_open()
      return dict(self._kv)

  # --------------- Set

  def set(self, key: str, value: Any) -> bool:
    with self._lock:
      self._ensure_open()

      old_exists = key in self._kv
      old_value = self._kv.get(key)

      self._kv[key] = value

      # Persist immediately.
      if self.save():
        return True

      # Rollback on save failure.
      if old_exists:
        self._kv[key] = old_value
      else:
        self._kv.pop(key, None)

      return False

  # --------------- Get or Set

  def get_or_set(self, key: str, value: Any) -> Any:
    with self._lock:
      self._ensure_open()

      if key in self._kv:
        return self._kv[key]

      self._kv[key] = value

      if self.save():
        return value

      self._kv.pop(key, None)

      raise OSError("Failed to persist key-value data")

  # --------------- Has

  def has(self, key: str) -> bool:
    with self._lock:
      self._ensure_open()
      return key in self._kv

  # --------------- Pop

  def pop(self, key: str) -> Any:
    with self._lock:
      self._ensure_open()

      if key not in self._kv:
        raise KeyError("Key not found")

      old_value = self._kv.pop(key)

      if self.save():
        return old_value

      # Rollback if save failed.
      self._kv[key] = old_value

      raise OSError("Failed to persist key-value data")

  # --------------- Info

  def info(self) -> dict[str, Any]:
    with self._lock:
      self._ensure_open()

      return {
        "id": self.id,
        "app_name": self.app_name,
        "app_id": self.app_id,
        "dfile_path": str(self.dfile_path),
        "length": len(self._kv),
      }

  # --------------- Lifecycle

  def _close(self) -> None:
    self.save()

  def close(self) -> None:
    with self._lock:
      if self.__closed:
        return

      # Save while still open.
      self.save()
      self.__closed = True

  def __str__(self):
    return (
      f"Collection ID={self.id} "
      f"APP={self.app_name} "
      f"DPATH={self.dfile_path}"
    )


# --------------- KVM

class KVM:
  def __init__(self) -> None:
    # App ID -> Collection
    self._collections: dict[str, Collection] = {}
    self._lock = threading.RLock()

  def get_collection(self, core: Any, app: Any) -> Collection:
    app_id = str(app.id)

    with self._lock:
      collection = self._collections.get(app_id)

      if collection is not None:
        return collection

      dfile_path = (
        ensure_dir(
          app.get_app_data_local_path()
          / "services"
          / "kv"
        )
        / "data.json"
      ).resolve()

      collection = Collection(
        app_name=app.name,
        app_id=app_id,
        dfile_path=dfile_path,
      )

      self._collections[app_id] = collection

      logger.info(
        "Service(KV) Collection initialized: "
        "App=%s ID=%s Collection=%s",
        app.name,
        app_id,
        collection,
      )

      return collection

  # --------------- LIFECYCLE

  async def on_close_app(
    self,
    app_id: str,
    app_name: str,
  ) -> None:
    core = srv.get_core()

    # If another app with the same name still exists,
    # don't close anything yet.
    if len(core.get_apps_by_name(app_name)) > 0:
      return

    collection = None

    with self._lock:
      # Prefer app ID.
      collection = self._collections.pop(str(app_id), None)

      # Fallback for older/inconsistent lifecycle events.
      if collection is None:
        for cid, candidate in list(self._collections.items()):
          if candidate.app_name == app_name:
            collection = self._collections.pop(cid)
            break

    if collection is not None:
      await asyncio.to_thread(collection.close)

      logger.info(
        "Service(KV) Collection closed for %s ID=%s",
        app_name,
        app_id,
      )

  def on_shutdown(self) -> None:
    with self._lock:
      collections = list(self._collections.values())
      self._collections.clear()

    for collection in collections:
      try:
        collection.close()
      except Exception:
        logger.exception(
          "Service(KV): error closing collection %s",
          collection,
        )


kvm = KVM()


# --------------- Lifecycle

@srv.on("startup")
def startup(core: Any) -> None:
  core.events.add_event("app:close", kvm.on_close_app)


@srv.on("shutdown")
def shutdown(core: Any) -> None:
  kvm.on_shutdown()


# --------------- Routes

# Info
@srv.router.get("/info")
def info(
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  return kvm.get_collection(core, app).info()


# Get value by key
@srv.router.get("/get")
def get(
  key: str,
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  c = kvm.get_collection(core, app)

  exists = c.has(key)
  value = c.get(key) if exists else None

  return {
    "key": key,
    "exists": exists,
    "value": value,
  }


# Set key/value
@srv.router.post("/set")
def set(
  payload: SetCollectionModel,
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  c = kvm.get_collection(core, app)

  if not c.set(payload.key, payload.value):
    srv.exception(500, "Failed to save key-value data")

  return {
    "key": payload.key,
    "value": payload.value,
  }


# Check if key exists
@srv.router.get("/exists")
def exists(
  key: str,
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  return kvm.get_collection(core, app).has(key)


# Get or set
@srv.router.post("/get-set")
def get_or_set(
  payload: SetCollectionModel,
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  try:
    return kvm.get_collection(core, app).get_or_set(
      payload.key,
      payload.value,
    )
  except OSError:
    srv.exception(500, "Failed to save key-value data")


# Pop / Delete
@srv.router.delete("/pop")
def pop_key(
  key: str,
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  try:
    return kvm.get_collection(core, app).pop(key)

  except KeyError as e:
    srv.exception(404, str(e))

  except OSError:
    srv.exception(500, "Failed to save key-value data")


# Dump data
@srv.router.get("/dump")
def get_all(
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  return kvm.get_collection(core, app).dump()


# Explicit save
@srv.router.post("/save")
def save_collection(
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  if not kvm.get_collection(core, app).save():
    srv.exception(500, "Failed to save key-value data")

  return srv.ok()


# Reset
@srv.router.post("/reset")
def reset_collection(
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  if not kvm.get_collection(core, app).reset():
    srv.exception(500, "Failed to save key-value data")

  return True

