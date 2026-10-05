import os
import json
import logging
import tempfile
import threading

from typing import Any
from pathlib import Path
from pydantic import BaseModel

from fastapi import Request, Depends

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
    srv.exception(
      403,
      "Service 'kv' not found in config",
    )

  return core


# --------------- Collection

class Collection:
  """
  Shared KV collection for one application.

  Multiple runtime instances of the same application share the
  same Collection object inside this service worker.

  The RLock protects the in-memory collection from concurrent
  requests.

  The JSON file is used for persistence only.
  """

  def __init__(
    self,
    app_name: str,
    created_app_id: str,
    dfile_path: Path,
  ):
    self.id: str = generate_uuid()
    self.app_name: str = app_name
    self.created_app_id: str = created_app_id
    self.dfile_path: Path = dfile_path

    self._lock = threading.RLock()
    self.__closed = False

    self.dfile_path.parent.mkdir(
      parents=True,
      exist_ok=True,
    )

    self._kv: dict[str, Any] = self.load(
      self.dfile_path
    )

  # --------------- Internal

  def _ensure_open(self) -> None:
    if self.__closed:
      raise RuntimeError("Collection is closed")

  # --------------- Load

  def load(self, dfile: Path) -> dict[str, Any]:
    if not dfile.is_file():
      return {}

    try:
      with dfile.open(
        "r",
        encoding="utf-8",
      ) as file:
        data = json.load(file)

      if not isinstance(data, dict):
        logger.error(
          "Service(KV): invalid data format in %s; "
          "expected object",
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

  def _save_locked(self) -> bool:
    """
    Save the current collection atomically.

    Caller must hold self._lock.

    A unique temporary file is used for every save so concurrent
    save attempts cannot collide on the same data.tmp file.
    """

    data = dict(self._kv)

    parent = self.dfile_path.parent
    tmp_path: Path | None = None
    fd: int | None = None

    try:
      parent.mkdir(parents=True, exist_ok=True)

      # Create a unique temporary file in the same directory.
      #
      # Keeping it in the same directory allows os.replace()
      # to remain atomic.

      fd, tmp_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{self.dfile_path.name}.",
        suffix=".tmp",
      )

      tmp_path = Path(tmp_name)

      with os.fdopen(
        fd,
        "w",
        encoding="utf-8",
      ) as file:
        fd = None

        json.dump(
          data,
          file,
          ensure_ascii=False,
          separators=(",", ":"),
        )

        file.flush()

        # Make sure the data reaches the OS before replacement.
        os.fsync(file.fileno())

      # Atomically replace the old data file.
      os.replace(tmp_path, self.dfile_path)

      tmp_path = None

      return True

    except (
      OSError,
      TypeError,
      ValueError,
    ):
      logger.exception(
        "Service(KV): error saving datafile: %s",
        self.dfile_path,
      )

      if fd is not None:
        try:
          os.close(fd)
        except OSError:
          pass

      if tmp_path is not None:
        try:
          tmp_path.unlink(missing_ok=True)
        except OSError:
          pass

      return False

  def save(self) -> bool:
    with self._lock:
      self._ensure_open()

      return self._save_locked()

  # --------------- Reset

  def reset(self) -> bool:
    with self._lock:
      self._ensure_open()

      old_kv = self._kv

      self._kv = {}

      if self._save_locked():
        return True

      # Rollback if saving failed.
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

      return self._kv.get(
        key,
        fallback,
      )

  # --------------- Dump

  def dump(self) -> dict[str, Any]:
    with self._lock:
      self._ensure_open()

      return dict(self._kv)

  # --------------- Set

  def set(
    self,
    key: str,
    value: Any,
  ) -> bool:
    with self._lock:
      self._ensure_open()

      old_exists = key in self._kv
      old_value = self._kv.get(key)

      self._kv[key] = value

      if self._save_locked():
        return True

      # Rollback if saving failed.
      if old_exists:
        self._kv[key] = old_value
      else:
        self._kv.pop(key, None)

      return False

  # --------------- Get or Set

  def get_or_set(
    self,
    key: str,
    value: Any,
  ) -> Any:
    with self._lock:
      self._ensure_open()

      if key in self._kv:
        return self._kv[key]

      self._kv[key] = value

      if self._save_locked():
        return value

      # Rollback if saving failed.
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

      if self._save_locked():
        return old_value

      # Rollback if saving failed.
      self._kv[key] = old_value

      raise OSError("Failed to persist key-value data")

  # --------------- Info

  def info(self) -> dict[str, Any]:
    with self._lock:
      self._ensure_open()

      return {
        "id": self.id,
        "app_name": self.app_name,
        "created_app_id": self.created_app_id,
        "dfile_path": str(
          self.dfile_path
        ),
        "length": len(self._kv),
      }

  # --------------- Lifecycle

  def _close(self) -> None:
    self.close()

  def close(self) -> None:
    with self._lock:
      if self.__closed:
        return

      try:
        self._save_locked()

      finally:
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
    # Stable application identity -> Collection.
    #
    # app.id must NOT be used here because every runtime
    # instance can have a different ID.
    #
    # app.name identifies the actual application.

    self._collections: dict[str, Collection] = {}

    self._lock = threading.RLock()

  def get_collection(
    self,
    core: Any,
    app: Any
  ) -> Collection:
    app_key = str(app.name)

    with self._lock:
      collection = self._collections.get(app_key)

      if collection is not None:
        return collection

      # One persistent KV collection per application.

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
        created_app_id=app.id,
        dfile_path=dfile_path,
      )

      self._collections[app_key] = collection

      logger.info(
        "Service(KV) Collection initialized: "
        "App=%s Collection=%s",
        app.name,
        collection,
      )

      return collection

  # --------------- Lifecycle

  async def on_close_app(self, _, app_name: str) -> None:
    core = srv.get_core()

    # If another runtime instance of this application is still
    # running, keep the shared collection alive.

    if len(core.get_apps_by_name(app_name)) > 0:
      return

    with self._lock:
      collection = self._collections.pop(
        str(app_name),
        None,
      )

    if collection is not None:
      collection.close()

      logger.info(
        "Service(KV) Collection closed for %s",
        app_name,
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

  value = (c.get(key) if exists else None)

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
    srv.exception(
       500,
      "Failed to save key-value data",
    )

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
    return kvm.get_collection(
      core,
      app,
    ).get_or_set(
      payload.key,
      payload.value,
    )

  except OSError:
    srv.exception(
      500,
      "Failed to save key-value data",
    )


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
    srv.exception(
      500,
      "Failed to save key-value data",
    )


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
    srv.exception(
      500,
      "Failed to save key-value data",
    )

  return srv.ok("Saved collection")


# Reset

@srv.router.post("/reset")
def reset_collection(
  request: Request,
  core=Depends(check_permisson),
  app=Depends(get_app),
):
  if not kvm.get_collection(core, app).reset():
    srv.exception(
      500,
      "Failed to save key-value data",
    )

  return srv.ok("Succesfully reset")