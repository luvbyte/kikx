import os
import logging
from fastapi import APIRouter, Request, Depends

from lib.service import create_service

from typing import List, Any, Dict
from pydantic import BaseModel


logger = logging.getLogger(__name__)


def check_permisson(request: Request):
  core = srv.get_core()

  client, app = srv.get_client_or_app(request)
  if app is None: # allow access for clients
    return core

  # If app - check os exists in app config
  if not app.config.os:
    srv.exception(403, "Require 'os' permission")

  return core


srv = create_service(__file__)

# -------------- Models
class OSCommandModel(BaseModel):
  name: str
  args: List[Any]
  options: Dict[str, Any]


# -------------- OSC

class OSC:

  # -------------- Funcs ex_<name>
  def ex_echo(self, *args, **options):
    return { "args": args, "options": options }

  # --------------
  
  def _run(self, name: str, args, options):
    func = getattr(self, f"ex_{name}", None)
    if func is None:
      srv.exception(404, "Func not found")

    try:
      return func(*args, **options)
    except Exception as e:
      srv.exception(500, e)

  def run_client(self, client, payload):
    return self._run(payload.name, payload.args, payload.options)

  def run_app(self, app, payload):
    return self._run(payload.name, payload.args, payload.options)


# -------------- ROUTES

osc = OSC()

@srv.router.post("/run")
def run(payload: OSCommandModel, request: Request, core = Depends(check_permisson)):
  client, app = srv.get_client_or_app(request)
  
  if app:
    return osc.run_app(app, payload)
  else:
    return osc.run_client(client, payload)
  
