import asyncio
from uuid import uuid4
from typing import Literal, Optional

from fastapi import Request, HTTPException

from core.func.func import FuncXModel

from lib.utils import get_timestamp
from lib.service import create_service

from .routes import info, app
from .models import NotifyModel, UserSettingsModel, AlertModel, ClientAppEventModel



srv = create_service(__file__)


async def broadcast_signal(signal: str, data: dict) -> None:
  core = srv.get_core()
  payload = { "signal": signal, "data": data }

  for client in core.clients.values():
    await client.send_event("signal", payload)
    for a in client.running_apps.values():
      await a.send_event("signal", payload)

# ------ App FuncX 
@srv.router.post("/app/func")
async def app_func(request: Request, app_func_model: FuncXModel):
  client, app = srv.get_client_app(request)
  if not app.config.system.check("funcx"):
    raise HTTPException(status_code=403, detail="Permission denied")

  try:
    return await app.run_function(app_func_model)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# ------ Client FuncX 
@srv.router.post("/client/func")
async def client_func(request: Request, client_func_model: FuncXModel):
  client = srv.get_client(request)
  try:
    return await client.run_function(client_func_model)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e),)

# ------ Sending app close event to client
@srv.router.post("/close-app") # triggers app for closing itself
async def close_app(request: Request) -> None:
  client, app = srv.get_client_app(request)
  await client.send_event("app:close", {
    "appID": app.id,
    "name": app.name
  })

# ------ Client logout by itself
@srv.router.post("/client-logout")
async def client_logout(request: Request) -> None:
  client = srv.get_client(request)
  await srv.get_core().close_client(client.id)
  return { "res": "ok" }

# ------ Client to app event 
@srv.router.post("/client-app-event")
async def client_app_event(request: Request, payload: ClientAppEventModel):
  client = srv.get_client(request)
  
  app = client.get_app(payload.app_id)
  if app is None:
    raise HTTPException(status_code=404, detail="App not found")

  # Sending client-app event
  await app.send_event("client-app-event", {
    "event": payload.event,
    "payload": payload.payload
  })

# ------ Notify
@srv.router.post("/notify")
async def notify(request: Request, payload: NotifyModel) -> None:
  client, app = srv.get_client_app(request)
  if not app.config.system.check("notify"):
    raise HTTPException(status_code=403, detail="Permission denied")

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

# ------ Alert
@srv.router.post("/alert")
async def alert(request: Request, payload: AlertModel) -> None:
  client, app = srv.get_client_app(request)
  if not app.config.system.check("alert"):
    raise HTTPException(status_code=403, detail="Permission denied")

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
srv.include(info.router, prefix="/info", tags=["SystemService-Info"])

# ------ App Manage
srv.include(app.router, prefix="/app", tags=["SystemService-App"])

