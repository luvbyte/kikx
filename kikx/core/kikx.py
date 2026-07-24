import os
import asyncio
import logging
from datetime import datetime

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import (
  FastAPI, WebSocket, WebSocketDisconnect,
  Request, Cookie, HTTPException, Form
)
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.core import Core
from core.client import Client
from core.utils import load_app_manifest
from core.global_config import GlobalConfig
from core.models.app_models import AppOptionsModel

from lib.utils import file_response, import_relative_module

from core.logging import setup_logging


# -------------------------------------
# Logging Configuration
# -------------------------------------
gconfig = GlobalConfig()

STORAGE = gconfig.kikx.get_fs_path()
if not STORAGE.is_dir():
  print(f"\nFS path '{STORAGE}' not found Quiting.\n")
  exit()

setup_logging(
  os.path.join(STORAGE, "logs"),
  f"kikx_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

logger = logging.getLogger(__name__)

# -------------------------------------
# Core App Initialization
# -------------------------------------

core = Core(STORAGE, dev_mode=gconfig.kikx.dev_mode)


# Fastapi lifespan
async def lifespan(app: FastAPI):
  await core.on_start(app)
  core.scr.title("KIKX STARTED")

  if not core.is_dev_mode:
    server_config = core.config.kikx.server
    core.scr.print(f"http://{server_config.host}:{server_config.port}\n")

  yield # 

  await core.on_close()
  core.scr.title("KIKX SHUTDOWN")

# Create FastAPI instance
def __create_app():
  if core.is_dev_mode:
    return FastAPI(lifespan=lifespan)
  # Disable docs
  return FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
  )

# Fastapi
kikx_app = __create_app()
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
    
    # /dev route for testing & inspection
    if module_name == "dev" and not core.is_dev_mode:
      continue

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
  
  options: AppOptionsModel = Field(default_factory=AppOptionsModel)

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

@kikx_app.post("/open-app")
async def open_app(app_model: OpenAppModel):
  info, manifest = load_app_manifest(core, app_model.name, both=True)

  app = await core.open_app(app_model.client_id, app_model.name, manifest, app_model.options)

  return {
    "id": app.id,
    "url": f"/app/{app.id}/index.html?starting=true",
    "iframe": app.config.iframe.get_dict(),

    "manifest": info, # Simple info for ui

    "isSudo": app.is_sudo
  }

@kikx_app.post("/close-app")
async def close_app(app_model: CloseAppModel):
  client, app = core.get_client_app_by_id(app_model.app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="Unauthorized")

  asyncio.create_task(core.close_app(client, app))
  return { "res": "ok" }

# -------------------------------------
# File Routes
# -------------------------------------

@kikx_app.get("/app/{app_id}/{path:path}")
async def app_web(app_id: str, path: str, starting: bool = False):
  """App files located in www"""
  client, app = core.get_client_app_by_id(app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="App not found")

  return file_response(app.app_path, (path.replace("_app/", "") if path.startswith("_app/") else f"www/{path}"))

@kikx_app.get("/app-data/{app_id}/{path:path}")
async def app_data(app_id: str, path: str, starting: bool = False):
  """App data files"""
  client, app = core.get_client_app_by_id(app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="App not found")

  return file_response(app.get_app_data_path(), path)

@kikx_app.get("/ui/{ui_name}/{path:path}")
def home_page(request: Request, ui_name: str, path: str):
  """UI files located in www"""
  path = "index.html" if not path.strip() else path
  # Require access for index page
  if path == "index.html":
    token = request.cookies.get("access_token")
    if not core.auth.check_access_token(token):
      return RedirectResponse(f"/login?ui={ui_name}")
  # Checking if ui enabled
  if ui_name not in core.auth.user_config.ui:
    raise HTTPException(status_code=404, detail="UI not found in auth.json")

  return file_response(core.config.uis_path, ui_name, "www", path)

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

    # Unauthorized
    if not client or not app:
      raise PermissionError("Unauthorized")
    
    # new connection
    if app.connection.new_connection:
      event_name = "connected"

    await app.connect_websocket(websocket)

    # Sending connected / reconnected event with app config
    await app.send_event(event_name, {
      "config": client.get_app_config(app)
    })
  except PermissionError as e:
    await websocket.close(code=1008, reason=str(e))
    return
  except Exception as e:
    logger.info(f"WebSocket App Connect Error: {str(e)}")
    await websocket.close(reason=str(e))
    return

  logger.info(f"WebSocket: App connected {app.id} (Client: {client.id})")

  while True:
    try:
      print(websocket, websocket.client_state, websocket.application_state)
      
      data = await websocket.receive_json()
      logger.debug(f"WebSocket Data (App {app.id}): {data}")

      await core.on_app_data(client, app, data)
    except WebSocketDisconnect:
      logger.info(f"WebSocket: App disconnected {app.id}")
      break
    except RuntimeError as e:
      logger.exception(f"Runtime error app {client.id}: {e}")
      break
    except Exception as e:
      logger.exception(f"WebSocket receive error {app.id}: {e}")
      break

  await app.connection.close(websocket)

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
      client = Client(core.user, core.config.resolve_path, access_token, ui)
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
    logger.exception(f"WebSocket Client Connect Error: {str(e)}")
    await websocket.close(reason=str(e))
    return

  logger.info(f"WebSocket: Client connected (ID: {client.id})")

  while True:
    try:
      data = await websocket.receive_json()
      await core.on_client_data(client, data)
    except WebSocketDisconnect:
      logger.info(f"Client {client.id} disconnected")
      break
    except RuntimeError as e:
      logger.exception(f"Runtime error client {client.id}: {e}")
      break
    except Exception as e:
      logger.exception(f"Error handling client {client.id}: {e}")
      break

  # Try closing
  await client.connection.close(websocket)

