# -------------------------------------
# Imports
# -------------------------------------
import logging
import asyncio
from fastapi import (
  FastAPI, WebSocket, WebSocketDisconnect, APIRouter,
  Request, Response, Depends, Cookie, HTTPException, Form
)
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from pydantic import BaseModel
from typing import Optional

from lib.utils import dynamic_import, is_websocket_connected
from lib.plugins import KikxPlugin
from lib.parser import parse_config

from core.core import Core
from core.client import Client
from core.models.app_models import CloseAppModel, OpenAppModel, AppsListModel, AppManifestModel

from lib.utils import file_response

from datetime import timedelta
# -------------------------------------
# Logging Configuration
# -------------------------------------

logging.basicConfig(level=logging.INFO, format="\n%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("kikx")

# -------------------------------------
# Core App Initialization
# -------------------------------------

core = Core()

async def lifespan(_: FastAPI):
  await core.on_start()
  logger.info("<=== [ KIKX STARTED ] ===>")
  yield
  print("before lifespan yield")
  await core.on_close()
  logger.info("<=== [ KIKX CLOSED ] ===>")

kikx_app = FastAPI(lifespan=lifespan)

# Load plugins
core.plugins.load(core)
core.plugins.before_startup(KikxPlugin(core, kikx_app))
core.services.load(core, kikx_app)

# CORS Middleware
kikx_app.add_middleware(
  CORSMiddleware,
  allow_origins=["*", "null"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Static file mounts
kikx_app.mount("/share", StaticFiles(directory=core.config.share_path), name="share")
kikx_app.mount("/files", StaticFiles(directory=core.config.files_path), name="files")

# -------------------------------------
# API Router
# -------------------------------------

api = APIRouter()

# App manifest like name, title, icon
def load_app_manifest(name: str):
  manifest_path = (core.config.apps_path / name / "app.json").resolve()
  if not manifest_path.exists():
    raise HTTPException(status_code=404, detail="File not found")

  # checking relative paths
  if not manifest_path.is_relative_to(core.config.apps_path):
    raise HTTPException(status_code=403, detail="Forbidden path")

  # Parsing file
  manifest = parse_config(manifest_path, AppManifestModel)

  return {
    "name": name,
    "title": manifest.title,
    "icon": f"/public/app/{name}/{manifest.icon}",
    
    "theme": manifest.theme
  }

@api.post("/apps/list")
def get_apps_list(data: AppsListModel):
  client = core.clients.get(data.client_id)
  if client is None:
    raise HTTPException(status_code=401, detail="Client not found")
  
  def safe_load(name):
    try:
      return load_app_manifest(name)
    except Exception:
      return None
  
  return [res for name in client.user.get_installed_apps() if (res := safe_load(name)) is not None]

@api.get("/ui-list")
def get_ui_list():
  return {
    "ui": list(core.auth.user_config.ui),
    "default": core.auth.user_config.default_ui
  }

# Include API routes
kikx_app.include_router(api, prefix="/api", tags=["Api"])

# -------------------------------------
# Auth Routes
# -------------------------------------
@kikx_app.get("/login", tags=["Auth"])
def login_page(file: Optional[str] = None, ui: Optional[str] = None):
  return file_response("www/auth", "login.html")

@kikx_app.post("/login", tags=["Auth"])
async def login(access: str = Form(...)):
  access_token = core.auth.generate_access_token(access)
  if not access_token:
    raise HTTPException(status_code=401, detail="Invalid credentials")
  response = JSONResponse(content={"message": "Login successful"})
  response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="strict")
  #max_age=None,   # No explicit max age
  #expires=None    # No explicit expiry time
  return response

@kikx_app.get("/logout", tags=["Auth"])
def logout():
  response = RedirectResponse("/")
  response.delete_cookie("access_token")
  return response

@kikx_app.get("/generate", tags=["Auth"])
def generate(key: str):
  access_token = core.auth.generate_access_token(key)
  return {
    "access_token": access_token
  }

# -------------------------------------
# App Lifecycle
# -------------------------------------

@kikx_app.post("/close-app")
async def close_app(app_model: CloseAppModel):
  client, app = core.get_client_app_by_id(app_model.app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="Unauthorized")
  try:
    asyncio.create_task(core.close_app(client, app))
    return { "res": "ok" }
  except Exception as e:
    logger.exception(f"Error closing app {e}")
    raise HTTPException(status_code=500, detail=f"Can't close app - {e}")

@kikx_app.post("/open-app")
async def open_app(app_model: OpenAppModel):
  try:
    app = await core.open_app(app_model.client_id, app_model.name, load_app_manifest(app_model.name), app_model.sudo)

    return {
      "id": app.id,
      "url": f"/app/{app.id}/index.html?starting=true",
      "iframe": app.config.iframe,

      "manifest": app.manifest,
      "isSudo": app.sudo
    }
  except Exception as e:
    raise HTTPException(status_code=401, detail=str(e))

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

@kikx_app.get("/public/app/{name}/{path:path}")
async def app_public(name: str, path: str):
  return file_response(core.config.apps_path, name, "public", path)

@kikx_app.get("/public/ui/{name}/{path:path}")
async def ui_public(name: str, path: str):
  return file_response(core.config.uis_path, name, "public", path)

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

@kikx_app.get("/sl/{path:path}")
def redirect(path: str):
  try:
    return RedirectResponse(core.shortlink.resolve(path))
  except Exception as e:
    raise HTTPException(status_code=404, detail=str(e))
  

@kikx_app.get("/lazy-login")
def lazy_login(key: str):
  access_token = core.auth.generate_access_token(key)
  if not access_token:
    raise HTTPException(status_code=401, detail="Invalid credentials")
  response = RedirectResponse("/")
  response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="strict")
  
  return response

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
      "config": app.config.model_dump()
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
    logger.info(f"Connect Aatempt: {websocket} ClientID: {client_id} Access: {access_token}")
    event_name = "reconnected"
    # if client found then no need for access_token
    client = core.clients.get(client_id)
    # if no client found then created one based on access_token
    if not client:
      # If access token already exists then disconnect previous client based on that
      # ----- no need access token for already connected session
      if core.auth.pop_access_token(access_token) is None:
        raise PermissionError("Unauthorized")
      # move this above to check even client reconnect
      client = Client(core.user, core.config.resolve_path, access_token)
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

  logger.info(f"WebSocket: Client connected {client.id}")

  try:
    while True:
      data = await websocket.receive_json()
      await core.on_client_data(client, data)
  except WebSocketDisconnect:
    logger.info(f"WebSocket: Client {client.id} disconnected ACTIVE: {core.clients}")
  except Exception as e:
    logger.exception(f"WebSocket client error: {e}")

# -------------------------------------
# Final plugin hook
# -------------------------------------

core.plugins.after_startup(KikxPlugin(core, kikx_app))
