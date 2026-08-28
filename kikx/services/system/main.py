from fastapi import Request

from core.func.func import FuncXModel

from lib.utils import get_timestamp, generate_uuid
from lib.service import create_service

from .routes import info, app
from .models import AlertModel, ClientAppEventModel, InvokeModel



srv = create_service(__file__)


# ------ App FuncX 
@srv.router.post("/app/func")
async def app_func(request: Request, app_func_model: FuncXModel):
  client, app = srv.get_client_app(request)
  if not app.config.system.check("funcx"):
    srv.exception(403, "Permission denied")
  try:
    return await app.run_function(app_func_model)
  except Exception as e:
    srv.exception(500, e)

# ------ Client FuncX 
@srv.router.post("/client/func")
async def client_func(request: Request, client_func_model: FuncXModel):
  client = srv.get_client(request)
  try:
    return await client.run_function(client_func_model)
  except Exception as e:
    srv.exception(500, e)

# Sending self app close event to client
@srv.router.post("/close-app")
async def close_app(request: Request) -> None:
  client, app = srv.get_client_app(request)
  await client.send_event("app:close", {
    "id": app.id,
    "name": app.name
  })

  return srv.ok()

# Client logout by itself
@srv.router.post("/client-logout")
async def client_logout(request: Request) -> None:
  client = srv.get_client(request)
  await srv.get_core().close_client(client.id)

  return srv.ok()

# ------ Client to app event 
@srv.router.post("/client-app-event")
async def client_app_event(request: Request, payload: ClientAppEventModel):
  client = srv.get_client(request)
  
  app = client.get_app(payload.app_id)
  if app is None:
    srv.exception(404, "App not found")

  # Sending client-app event
  await app.send_event("client-app-event", {
    "event": payload.event,
    "payload": payload.payload
  })

# ------ Alert
@srv.router.post("/alert")
async def alert(request: Request, payload: AlertModel) -> None:
  client, app = srv.get_client_app(request)
  if not app.config.system.check("alert"):
    srv.exception(403, "Require 'alert' permission")

  alert_uid = payload.uid or generate_uuid()

  await client.send_event("app:alert", {
    "id": app.id,
    "uid": alert_uid, # alert unique id
    
    "silent": payload.silent,
    
    "name": app.name,
    "title": app.title,

    "icon": f"/public/app/{app.name}/{app.manifest.icon}",

    "label": payload.label if payload.label and len(payload.label) > 0 else None,
    "message": payload.message,
    "type": payload.type,
    "extra": payload.extra,
    "priority": payload.priority,
    
    "sticky": payload.sticky,
    
    # Add timestamp (ISO 8601, UTC)
    "createdAt": get_timestamp() #  datetime.now(timezone.utc).isoformat()
  })

  return { "uid": alert_uid }

# ------ Invoke
@srv.router.post("/invoke")
async def invoke(payload: InvokeModel, request: Request):
  client, app = srv.get_client_app(request)
  if not app.config.system.check("invoke"):
    srv.exception(403, "Require 'invoke' permission")

  core = srv.get_core()

  # ------ 
  if payload.action == "openApp":
    app_name = payload.payload.get("name", None)
    if app_name is None or not core.is_app_installed(app_name):
      srv.exception(404, "App not found")

    limit = app.data.get("invoke-app-limit", 0)
    if limit >= 20:
      srv.exception(403, "Invoke limit reached")

    request_sudo = payload.payload.get("sudo", False)
    
    # If app is not opened as sudo and requests sudo app opening
    if request_sudo and not app.is_sudo:
      srv.exception(403, "App must run as sudo to open app as sudo")

    await client.send_event("app:invoke", {
      "action": "openApp",
      "name": app_name,
      "args": payload.payload.get("args", []),
      "query": payload.payload.get("query", {}),
      # Invoker app must be sudo and require sudo to open as sudo
      "sudo": request_sudo,
      # App info
      "invoker": { "id": app.id, "name": app.name },
    })

    app.data.set("invoke-app-limit",  limit + 1)
  elif payload.action == "action":
    await client.send_event("app:invoke", {
      "action": "action",
      # Invoker App info
      "invoker": { "id": app.id, "name": app.name },
      "payload": payload.payload
    })

  return srv.ok()

# ------ SYSTEM / SESSIONS
srv.include(info.router, prefix="/info", tags=["SystemService-Info"])

# ------ App Manage
srv.include(app.router, prefix="/app", tags=["SystemService-App"])

