import asyncio
import logging

from fastapi import Request
from pydantic import BaseModel

from lib.service import create_service
from lib.utils import generate_uuid, get_timestamp

from .models import AlertModel, ClientAppEventModel, InvokeModel
from .routes import info, kpm
from core.models.kikx import KikxConfigModel, SCHEMA


logger = logging.getLogger(__name__)

srv = create_service(__file__)


# ---------------------- Models
class UpdateSettingsModel(BaseModel):
  config: KikxConfigModel


# ---------------------- Close App
@srv.router.get("/close-app")
async def close_app(request: Request) -> None:
  client, app = srv.get_client_app(request)

  await client.send_event("app:close", {
    "id": app.id,
    "name": app.name,
  })

  return srv.ok()


# ---------------------- Client Logout
@srv.router.post("/client-logout")
async def client_logout(request: Request) -> None:
  client = srv.get_client(request)

  await srv.get_core().close_client(client.id)

  return srv.ok()


# ---------------------- Client App Event
@srv.router.post("/client-app-event")
async def client_app_event(
  request: Request,
  payload: ClientAppEventModel,
):
  client = srv.get_client(request)

  app = client.get_app(payload.app_id)

  if app is None:
    srv.exception(404, "App not found")

  await app.send_event("client-app-event", {
    "event": payload.event,
    "payload": payload.payload,
  })


# ---------------------- Alert
@srv.router.post("/alert")
async def alert(
  request: Request,
  payload: AlertModel,
) -> None:
  client, app = srv.get_client_app(request)

  if not app.config.system.check("alerts"):
    srv.exception(403, "Require 'alerts' permission")

  alert_uid = payload.uid or generate_uuid()

  await client.send_event("app:alert", {
    "id": app.id,
    "uid": alert_uid,
    "silent": payload.silent,
    "name": app.name,
    "title": app.title,
    "icon": f"/public/app/{app.name}/{app.manifest.icon}",
    "label": payload.label if payload.label else None,
    "message": payload.message,
    "type": payload.type,
    "extra": payload.extra,
    "priority": payload.priority,
    "sticky": payload.sticky,
    "createdAt": get_timestamp(),
  })

  return {
    "uid": alert_uid,
  }


# ---------------------- Invoke
@srv.router.post("/invoke")
async def invoke(request: Request, payload: InvokeModel):
  client, app = srv.get_client_app(request)

  if not app.config.system.check("invoke"):
    srv.exception(403, "Require 'invoke' permission")

  core = srv.get_core()

  res_id = payload.res_id or generate_uuid()

  if payload.action == "openApp":
    app_name = payload.payload.get("name")

    if app_name is None or not core.is_app_installed(app_name):
      srv.exception(404, "App not found")

    request_sudo = payload.payload.get("sudo", False)

    # Only sudo apps can request another app to open as sudo.
    if request_sudo and not app.is_sudo:
      srv.exception(
        403,
        "App must run as sudo to open app as sudo",
      )

    await client.send_event("app:invoke", {
      "action": "openApp",
      "name": app_name,
      "args": payload.payload.get("args", []),
      "query": payload.payload.get("query", {}),
      "sudo": request_sudo,
      "invoker": {
        "id": app.id,
        "name": app.name,
        "res_id": res_id
      },
    })

  elif payload.action == "action":
    await client.send_event("app:invoke", {
      "action": "action",
      "invoker": {
        "id": app.id,
        "name": app.name,
        "res_id": res_id
      },
      "payload": payload.payload,
    })
  
  else:
    srv.exception(404, "Invoke action not found")

  return srv.ok()


# ---------------------- Kikx Settings
@srv.router.get("/kikx-config")
def get_kikx_config(
  request: Request,
  reset: bool = False,
):
  srv.get_client(request)

  core = srv.get_core()

  return {
    "schema": SCHEMA,
    "config": core.config.get_kikx_config(reset=reset),
  }


@srv.router.post("/kikx-config")
def update_kikx_config(
  request: Request,
  payload: UpdateSettingsModel,
):
  srv.get_client(request)

  core = srv.get_core()
  core.config.update_kikx_config(payload.config)

  return srv.ok()


# ---------------------- System / Sessions
srv.include(
  info.router,
  prefix="/info",
  tags=["SystemService-Info"],
)


# ---------------------- KPM
srv.include(
  kpm.router,
  prefix="/kpm",
  tags=["SystemService-Kpm"],
)