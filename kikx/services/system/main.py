from fastapi import Request, HTTPException
from core.func.func import FuncXModel
from pydantic import BaseModel
from typing import Literal, Optional

from lib.service import create_service
import asyncio

srv = create_service(__file__)

# checks and returns client

class NotifyModel(BaseModel):
  type: Literal['info', 'error'] = "info"
  frames: Optional[list[str]] = None
  displayEvenActive: bool = False
  delay: int = 0
  msg: str


@srv.router.post("/notify")
async def notify(request: Request, payload: NotifyModel):
  client, app = srv.get_client_app(request)

  #notification_id = client.user.system.notify(payload.msg)
  # emit here
  await client.send_event("app:notify", {
    "name": app.name,
    "title": app.title,
    "msg": payload.msg,
    "type": payload.type,
    "frames": payload.frames,
    "delay": payload.delay,
    "displayEvenActive": payload.displayEvenActive
  })

# @srv.router.post("/toast")

# only for app
@srv.router.get("/user-settings")
def get_user_settings(request: Request, raw: bool = False):
  client, app = srv.get_client_app(request)
  return client.user.settings.raw if raw else client.user.settings.parsed

class UserSettingsModel(BaseModel):
  settings: dict
  
async def broadcast_signal(signal, data):
  core = srv.get_core()
  
  data = { "signal": signal, "data": data }

  for client in core.clients.values():
    # sending signal to client
    await client.send_event("signal", data)
    # sending for apps
    for app in client.running_apps.values():
      await app.send_event("signal", data)

@srv.router.post("/user-settings")
async def set_user_settings(request: Request, payload: UserSettingsModel):
  client, app = srv.get_client_app(request)
  app.user.settings.update(payload.settings)
  
  await broadcast_signal("update_user_settings", client.user.settings.parsed)

  return { "res": "updated success" }

# can work with app only
@srv.router.post("/app/func")
async def app_func(request: Request, app_func_model: FuncXModel):
  client, app = srv.get_client_app(request)

  try:
    return await app.run_function(app_func_model)
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=str(e), # implement errors
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

