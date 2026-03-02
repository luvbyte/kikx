import os
import asyncio
from fastapi import (
  FastAPI, WebSocket, WebSocketDisconnect,
  Request, Cookie, HTTPException, Form
)
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from typing import Optional
from pydantic import BaseModel, Field

from core.core import Core
from core.ui import ClientUI
from core.client import Client
from core.logging import Logger
from core.console import Console
from core.utils import load_app_manifest

from lib.utils import file_response, import_relative_module



# -------------------------------------
# Logging Configuration
# -------------------------------------

logging = Logger("kikx", "kikx_server.log")
logger = logging.get_logger()

# storage
STORAGE = os.environ.get("KIKXFS", "../kikxfs")

# -------------------------------------
# Core App Initialization
# -------------------------------------

core = Core(STORAGE, dev_mode=True)


# Fastapi lifespan
async def lifespan(app: FastAPI):
  await core.on_start(app)
  core.scr.print_divider("KIKX STARTED")

  if not core.is_dev_mode:
    server_config = core.config.kikx.server
    core.scr.print(f"http://{server_config.host}:{server_config.port}\n")

  yield # 
  
  await core.on_close()
  core.scr.print_divider("KIKX SHUTDOWN")

# Fastapi
kikx_app = FastAPI(lifespan=lifespan)
kikx_app.state.core = core # setting core as state

# CORS Middleware
kikx_app.add_middleware(
  CORSMiddleware,
  allow_origins=["*", "null"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Global exception handler
@kikx_app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
  if request.scope["type"] == "websocket":
    raise exc  # Let

  if core.is_dev_mode:
    logger.exception("Unhandled exception")
  else:
    logger.error(f"Error({type(exc).__name__}): {exc}")

  return JSONResponse(
    status_code=500,
    content={
      "success": False,
      "detail": "Internal server error"
    },
  )

# Static file mounts
kikx_app.mount("/share", StaticFiles(directory=core.config.share_path), name="share")
kikx_app.mount("/files", StaticFiles(directory=core.config.files_path), name="files")

# -------------------------------------
# Dynamically loading routes
# -------------------------------------
# Dynamically loading routes
for file in os.listdir("core/routes"):
  if file.endswith(".py") and file not in ("__init__.py",):
    module_name = file[:-3]  # remove .py
    module = import_relative_module(f"core.routes.{module_name}", module_name)

    # attach router if exists
    if hasattr(module, "router"):
      kikx_app.include_router(getattr(module, "router"), prefix=f"/{module_name}", tags=[module_name.capitalize()])

# -------------------------------------
# Models
# -------------------------------------

class CloseAppModel(BaseModel):
  app_id: str = Field(..., description="App ID")
  client_id: str = Field(..., description="Client ID")

# Close app router model
class OpenAppModel(BaseModel):
  name: str = Field(..., description="App name")
  client_id: str = Field(..., description="Client ID")
  sudo: bool = Field(False, description="Does app always need sudo permission")

# -------------------------------------
# Auth Routes
# -------------------------------------
@kikx_app.get("/login", tags=["Auth"])
def login_page(file: Optional[str] = None, ui: Optional[str] = None):
  return file_response("web/auth", "login.html")

@kikx_app.post("/login", tags=["Auth"])
async def login(access: str = Form(...), ui: str = Form(...)):
  access_token = core.auth.generate_access_token(access, ui)

  response = JSONResponse(content={"message": "Login successful"})
  response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="strict")
  #max_age=None,   # No explicit max age
  #expires=None    # No explicit expiry time
  return response

@kikx_app.get("/lazy-login", tags=["Auth"])
def lazy_login(key: str, ui: str):
  access_token = core.auth.generate_access_token(key, ui)

  response = RedirectResponse("/")
  response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="strict")
  
  return response

@kikx_app.get("/logout", tags=["Auth"])
def logout():
  response = RedirectResponse("/login")
  response.delete_cookie("access_token")
  return response

@kikx_app.get("/generate", tags=["Auth"])
def generate(key: str, ui: str):
  access_token = core.auth.generate_access_token(key, ui)
  return {"access_token": access_token}

# -------------------------------------
# App Lifecycle
# -------------------------------------

@kikx_app.post("/close-app")
async def close_app(app_model: CloseAppModel):
  client, app = core.get_client_app_by_id(app_model.app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="Unauthorized")

  asyncio.create_task(core.close_app(client, app))
  return { "res": "ok" }

@kikx_app.post("/open-app")
async def open_app(app_model: OpenAppModel):
  app = await core.open_app(app_model.client_id, app_model.name, load_app_manifest(core, app_model.name), app_model.sudo)

  return {
    "id": app.id,
    "url": f"/app/{app.id}/index.html?starting=true",
    "iframe": app.config.iframe.get_dict(),

    "manifest": app.manifest,
    "isSudo": app.sudo
  }
  
# -------------------------------------
# File Routes
# -------------------------------------

@kikx_app.get("/app/{app_id}/{path:path}")
async def app_web(app_id: str, path: str, starting: bool = False):
  client, app = core.get_client_app_by_id(app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="App not found")

  return file_response(app.app_path, (path.replace("_app/", "") if path.startswith("_app/") else f"www/{path}"))

# App data path
@kikx_app.get("/app-data/{app_id}/{path:path}")
async def app_data(app_id: str, path: str, starting: bool = False):
  client, app = core.get_client_app_by_id(app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="App not found")

  return file_response(app.get_app_data_path(), path)

@kikx_app.get("/ui/{ui_name}/{path:path}")
def home_page(request: Request, ui_name: str, path: str):
  path = "index.html" if not path.strip() else path
  # Require access for index page
  if path == "index.html":
    token = request.cookies.get("access_token")
    if not core.auth.check_access_token(token):
      return RedirectResponse(f"/login?ui={ui_name}")
  # Checking if ui enabled
  ui_config = core.config.kikx.ui.get(ui_name)
  if not ui_config or ui_name not in core.auth.user_config.ui:
    raise HTTPException(status_code=404, detail="UI not found in auth.json")

  return file_response(core.config.resolve_path(ui_config.path), "www", path)

@kikx_app.get("/")
def root_page(request: Request):
  return RedirectResponse("/ui/" + core.auth.user_config.default_ui)

# -------------------------------------
# WebSockets
# -------------------------------------

@kikx_app.websocket("/app/{app_id}")
async def apps_websocket_endpoint(websocket: WebSocket, app_id: str):
  await websocket.accept()
  client, app = core.get_client_app_by_id(app_id)

  try:
    event_name: str = "reconnected"
    
    if not client or not app:
      raise PermissionError("Unauthorized")
    # new connection
    if app.connection.websocket is None:
      event_name = "connected"
    await app.connect_websocket(websocket)
    await app.send_event(event_name, {
      "config": client.get_app_config(app)
      # "config": { **app.config.model_dump(), "ui": client.ui.name }
    })
  except PermissionError as e:
    await websocket.close(code=1008, reason=str(e))
    return
  except Exception as e:
    logger.info(f"WebSocket App Connect Error: {str(e)}")
    await websocket.close(reason=str(e))
    return

  logger.info(f"WebSocket: App connected {app.id} (Client: {client.id})")

  try:
    while True:
      data = await websocket.receive_json()
      logger.debug(f"WebSocket Data (App {app.id}): {data}")
      await core.on_app_data(client, app, data)
  except WebSocketDisconnect:
    logger.info(f"WebSocket: App disconnected {app.id}")

@kikx_app.websocket("/client")
async def websocket_client_endpoint(websocket: WebSocket, client_id: Optional[str] = None, access_token: str = Cookie(None)):
  await websocket.accept()

  try:
    logger.info(f"Cliend Connect Attempt (ID: {client_id}) (Access: {access_token})")
    event_name = "reconnected"
    # if client found then no need for access_token
    client = core.clients.get(client_id)
    # if no client found then created one based on access_token
    if not client:
      # If access token already exists then disconnect previous client based on that
      # ----- no need access token for already connected session
      if core.auth.pop_access_token(access_token) is None:
        raise PermissionError("Unauthorized")
  
      ui = access_token.split("_")[1]
      # move this above to check even client reconnect
      client = Client(core.user, core.config.resolve_path, access_token, ClientUI(ui, core.get_ui_config(ui)))
      core.clients[client.id] = client
      event_name = "connected"

    # This is reconnect attempt
    await client.connect_websocket(websocket)
    await client.send_event(event_name, {
      "client_id": client.id
    })
  except PermissionError as e:
    await websocket.close(code=1008, reason=str(e))
    return
  except Exception as e:
    logger.info(f"WebSocket Client Connect Error: {str(e)}")
    await websocket.close(reason=str(e))
    return

  logger.info(f"WebSocket: Client connected (ID: {client.id})")

  try:
    while True:
      data = await websocket.receive_json()
      await core.on_client_data(client, data)
  except WebSocketDisconnect:
    logger.info(f"WebSocket: Client {client.id} disconnected ACTIVE: {len(core.clients)}")
  except Exception as e:
    logger.exception(f"WebSocket client error: {e}")
