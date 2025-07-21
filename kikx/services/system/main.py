from typing import Literal, Optional

from fastapi import Request, HTTPException
from functools import reduce
from .models import NotifyModel, UserSettingsModel
from core.func.func import FuncXModel
from lib.service import create_service
import asyncio

srv = create_service(__file__)


async def broadcast_signal(signal: str, data: dict) -> None:
  core = srv.get_core()
  payload = { "signal": signal, "data": data }

  for client in core.clients.values():
    await client.send_event("signal", payload)
    for app in client.running_apps.values():
      await app.send_event("signal", payload)

@srv.router.get("/user-settings")
def get_user_settings(request: Request, setting: Optional[str] = None) -> dict:
  client, app = srv.get_client_app(request)
  try:
    settings =  client.user.settings
    return { "setting": reduce(getattr, setting.split("."), settings._settings) } if setting else settings()
  except Exception as e:
    srv.exception(404, str(e))

@srv.router.post("/user-settings")
async def set_user_settings(request: Request, payload: UserSettingsModel) -> dict:
  client, app = srv.get_client_app(request)
  try:
    app.user.settings.update(payload.settings)
    await broadcast_signal("update_user_settings", client.user.settings())
    return { "res": "updated success" }
  except Exception as e:
    srv.exception(401, f"Error updating settings : {e}")

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
