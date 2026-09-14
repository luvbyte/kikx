import logging

from typing import Any

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from lib.service import create_service


logger = logging.getLogger(__name__)

srv = create_service(__file__)


# ---------------------- Permission
def check_permission(request: Request):
  core = srv.get_core()

  client, app = srv.get_client_or_app(request)

  # Clients are allowed to access the service.
  if app is None:
    return core

  # Apps must have the OS service enabled.
  if not app.config.has_service("os"):
    srv.exception(403, "Service 'os' not found in config")

  return core


# ---------------------- Models
class OSCommandModel(BaseModel):
  name: str
  args: list[Any] = Field(default_factory=list)
  options: dict[str, Any] = Field(default_factory=dict)


# ---------------------- OSC
class OSC:
  @property
  def os(self):
    return srv.get_core().os

  # ---------------------- Functions
  def ex_username(self) -> str:
    return self.os.get_username()

  def ex_getenv(self, key: str, default=None) -> Any:
    return self.os.getenv(key, default)

  def ex_setenv(self, key, value) -> None:
    return self.os.setenv(key, value)

  def ex_unsetenv(self, key) -> Any:
    return self.os.unsetenv(key)

  def ex_environment(self) -> dict:
    return self.os.environment

  def ex_info(self) -> dict:
    os = self.os

    return {
      "username": os.username,
      "path": {
        "home": os.home,
        "cwd": os.cwd,
      },
      "info": os.info,
      "environment": os.environment,
    }

  # ---------------------- Execute
  def get_func(self, name: str):
    func = getattr(self, f"ex_{name}", None)

    if func is None:
      srv.exception(404, "Func not found")

    return func

  def _run(
    self,
    name: str,
    args: list[Any],
    options: dict[str, Any],
  ) -> Any:
    func = self.get_func(name)
    return func(*args, **options)

  def run_client(
    self,
    client: Any,
    payload: OSCommandModel,
  ) -> Any:
    return self._run(payload.name, payload.args, payload.options)

  def run_app(
    self,
    app: Any,
    payload: OSCommandModel,
  ) -> Any:
    return self._run(payload.name, payload.args, payload.options)


# ---------------------- Routes
osc = OSC()


@srv.router.post("/run")
def run(
  payload: OSCommandModel,
  request: Request,
  core=Depends(check_permission),
):
  client, app = srv.get_client_or_app(request)

  try:
    return osc.run_app(app, payload) if app else osc.run_client(client, payload)
  except HTTPException:
    raise
  except Exception as e:
    srv.exception(500, e)