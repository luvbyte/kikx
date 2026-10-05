import time

from pathlib import Path

from lib.utils import joinpath, generate_uuid


class ExposedPaths:
  def __init__(self, srv):
    self.srv = srv
    # ID: { id: str, root: Path, type: str, expires: float | None }
    self._exposed: dict = {}

  def exists(self, uid: str) -> bool:
    return uid in self._exposed

  # ---------------------- Checks
  def check_uid(self, uid: str) -> None:
    if not self.exists(uid):
      self.srv.exception(404, "uid not found")

  def get_expose(self, uid: str) -> dict:
    self.check_uid(uid)

    ex = self._exposed[uid]

    if ex["expires"] is not None and time.time() >= ex["expires"]:
      del self._exposed[uid]
      self.srv.exception(410, "uid expired")

    return ex

  def check(self, uid: str, _id: str, _type: str) -> None:
    ex = self.get_expose(uid)

    if ex["type"] != _type or ex["id"] != _id:
      self.srv.exception(404, "Forbidden")

  def check_app(self, uid: str, app_id: str) -> None:
    self.check(uid, app_id, "app")

  def check_client(self, uid: str, client_id: str) -> None:
    self.check(uid, client_id, "client")

  # ---------------------- Add
  def add(
    self,
    kikxpath: str,
    path: Path,
    _id: str,
    _type: str,
    expires: float | None,
  ) -> str:
    uid = generate_uuid()

    self._exposed[uid] = {
      "id": _id,
      "root": path,
      "kikxpath": kikxpath,
      "type": _type,
      "expires": time.time() + expires * 60 if expires is not None else None,
    }

    return uid

  # ---------------------- Remove
  def remove_app(self, uid: str, app_id: str) -> None:
    self.check_app(uid, app_id)
    del self._exposed[uid]

  def remove_client(self, uid: str, client_id: str) -> None:
    self.check_client(uid, client_id)
    del self._exposed[uid]

  # ---------------------- Clear
  def clear(self, _id: str, _type: str) -> int:
    exposed = [
      uid
      for uid, value in self._exposed.items()
      if value["type"] == _type and value["id"] == _id
    ]

    for uid in exposed:
      self._exposed.pop(uid, None)

    return len(exposed)

  def clear_app(self, app_id: str) -> int:
    return self.clear(app_id, "app")

  def clear_client(self, client_id: str) -> int:
    return self.clear(client_id, "client")

  # ---------------------- Serve
  def get_path(self, uid: str, path: str | None = None) -> Path:
    ex = self.get_expose(uid)
    root = ex["root"]
  
    kikxpath = ex["kikxpath"]

    if path:
      if kikxpath.endswith("://"):
        kikxpath = f"{kikxpath}{path.lstrip('/')}"
      else:
        kikxpath = f"{kikxpath.rstrip('/')}/{path.lstrip('/')}"

    return kikxpath, root / path if path else root