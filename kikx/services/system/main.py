from typing import Literal, Optional

from fastapi import Request, HTTPException
from functools import reduce
from .models import NotifyModel, UserSettingsModel, AlertModel
from core.func.func import FuncXModel
from lib.service import create_service
import asyncio

from lib.utils import get_timestamp

from uuid import uuid4

from .routes import info, app

srv = create_service(__file__)


async def broadcast_signal(signal: str, data: dict) -> None:
  core = srv.get_core()
  payload = { "signal": signal, "data": data }

  for client in core.clients.values():
    await client.send_event("signal", payload)
    for a in client.running_apps.values():
      await a.send_event("signal", payload)


@srv.router.post("/app/func")
async def app_func(request: Request, app_func_model: FuncXModel):
  client, app = srv.get_client_app(request)
  try:
    return await app.run_function(app_func_model)
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=str(e),
    )

@srv.router.post("/client/func")
async def client_func(request: Request, client_func_model: FuncXModel):
  client = srv.get_client(request)
  try:
    return await client.run_function(client_func_model)
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=str(e),
    )

@srv.router.post("/close-app")
async def close_app(request: Request) -> None:
  client, app = srv.get_client_app(request)
  await client.send_event("app:close", {
    "appID": app.id,
    "name": app.name
  })

@srv.router.post("/notify")
async def notify(request: Request, payload: NotifyModel) -> None:
  client, app = srv.get_client_app(request)

  await client.send_event("app:notify", {
    "name": app.name,
    "id": app.id,
    "title": app.title,
    "msg": payload.msg,
    "type": payload.type,
    "extra": payload.extra,
    "delay": payload.delay,
    "displayEvenActive": payload.displayEvenActive
  })

@srv.router.post("/alert")
async def alert(request: Request, payload: AlertModel) -> None:
  client, app = srv.get_client_app(request)

  await client.send_event("app:alert", {
    "id": app.id,
    "uid": uuid4().hex, # new
    "name": app.name,
    "title": app.title,
    
    "icon": app.manifest["icon"],

    "msg": payload.msg,
    "type": payload.type,
    "extra": payload.extra,
    "delay": payload.delay,
    "priority": payload.priority,
    
    # Add timestamp (ISO 8601, UTC)
    "createdAt": get_timestamp() #  datetime.now(timezone.utc).isoformat()
  })

# ------ SYSTEM / SESSIONS
srv.include(info.router, prefix="/info")

# ------ App Manage
srv.include(app.router, prefix="/app")

