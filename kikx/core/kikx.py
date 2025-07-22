# -------------------------------------
# Imports
# -------------------------------------
import logging
from fastapi import (
  FastAPI, WebSocket, WebSocketDisconnect, APIRouter,
  Request, Response, Depends, Cookie, HTTPException
)
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm

from pydantic import BaseModel

from lib.utils import dynamic_import, is_websocket_connected
from lib.plugins import KikxPlugin
from lib.parser import parse_config

from core.core import Core
from core.client import Client
from core.models.app_models import CloseAppModel, OpenAppModel, AppsListModel, AppManifestModel

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
  await core.on_close()
  logger.info("<=== [ KIKX CLOSED ] ===>")

app = FastAPI(lifespan=lifespan)

# Load plugins
core.plugins.load(core)
core.plugins.before_startup(KikxPlugin(core, app))
core.services.load(core, app)

# CORS Middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*", "null"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Static file mounts
app.mount("/share", StaticFiles(directory=core.config.share_path), name="share")
app.mount("/files", StaticFiles(directory=core.config.files_path), name="files")

# -------------------------------------
# API Router
# -------------------------------------

api = APIRouter()

@api.post("/apps/list")
def get_apps_list(data: AppsListModel, category: str | None = None):
  client = core.clients.get(data.client_id)
  if client is None:
    raise HTTPException(status_code=401, detail="Client not found")

  def get_app_icon_path(name, icon):
    icon_path = core.config.resolve_path("share://icons/app") / f"{name}.png"
    return f"/share/icons/app/{name}.png" if icon_path.exists() else f"/public/app/{name}/{icon}"

  def load_manifest(name):
    path = core.config.apps_path / name / "app.json"
    if not path.exists():
      return None
    try:
      manifest = parse_config(path, AppManifestModel)
      if category and category.lower() != (manifest.category or "").lower():
        return None
      return {
        "name": name,
        "title": manifest.title,
        "icon": get_app_icon_path(name, manifest.icon)
      }
    except Exception as e:
      logger.warning(f"Failed to load app manifest for {name}: {e}")
      return None

  apps = [app for app in map(load_manifest, client.user.get_installed_apps()) if app]
  return apps

# Include API routes
app.include_router(api, prefix="/api", tags=["Api"])

# -------------------------------------
# Auth Routes
# -------------------------------------

@app.get("/login", tags=["Auth"])
def login_page():
  return FileResponse("www/auth/login.html")

@app.post("/login", tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
  user = core.auth.authenticate_user(form_data.username, form_data.password)
  if not user:
    raise HTTPException(status_code=401, detail="Invalid credentials")

  token = core.auth.create_access_token(data={"sub": user})
  response = JSONResponse(content={"message": "Login successful"})
  response.set_cookie(key="access_token", value=token, samesite="strict", httponly=True)
  return response

@app.get("/logout", tags=["Auth"])
def logout():
  response = RedirectResponse("/")
  response.delete_cookie("access_token")
  return response

# -------------------------------------
# App Lifecycle
# -------------------------------------

@app.post("/close-app")
async def close_app(app_model: CloseAppModel):
  client, app = core.get_client_app_by_id(app_model.app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="Unauthorized")
  try:
    await core.close_app(client, app)
    return { "res": "ok" }
  except Exception as e:
    logger.exception("Error closing app")
    raise HTTPException(status_code=500, detail=f"Can't close app - {e}")

@app.post("/open-app")
def open_app(app_model: OpenAppModel):
  try:
    app = core.open_app(app_model.client_id, app_model.name)
    return {
      "id": app.id,
      "url": f"/app/{app.id}/index.html?starting=true",
      "iframe": app.config.iframe
    }
  except Exception as e:
    raise HTTPException(status_code=401, detail=str(e))

# -------------------------------------
# File Routes
# -------------------------------------

@app.get("/app/{app_id}/{path:path}")
async def app_web(app_id: str, path: str, starting: bool = False):
  client, app = core.get_client_app_by_id(app_id)
  if not client or not app:
    raise HTTPException(status_code=401, detail="App not found")

  file = app.app_path / (path.replace("_app/", "") if path.startswith("_app/") else f"www/{path}")
  if not file.exists():
    raise HTTPException(status_code=404, detail="File not found")

  return FileResponse(file)

@app.get("/public/app/{name}/{path:path}")
async def app_public(name: str, path: str):
  file = core.config.apps_path / name / "public" / path
  if not file.exists():
    raise HTTPException(status_code=404, detail="File not found")
  return FileResponse(file)

@app.get("/ui/{ui_name}/{path:path}")
def home_page(request: Request, ui_name: str, path: str):
  token = request.cookies.get("access_token")
  if not core.auth.check_token(token):
    return RedirectResponse("/login")

  ui_config = core.config.kikx.ui.get(ui_name)
  if not ui_config or ui_name not in core.auth.user_config.ui:
    raise HTTPException(status_code=404, detail="UI not found in auth.json")

  if not path.strip():
    path = "index.html"

  file_path = core.config.resolve_path(ui_config.path) / "www" / path
  if not file_path.exists() or file_path.is_dir():
    raise HTTPException(status_code=404, detail="File not found")
  
  return FileResponse(file_path)

@app.get("/sl/{path:path}")
def redirect(path: str):
  try:
    return RedirectResponse(core.shortlink.resolve(path))
  except Exception as e:
    raise HTTPException(status_code=404, detail=str(e))

@app.get("/")
def root_page(request: Request):
  return RedirectResponse("/ui/" + core.auth.user_config.default_ui)

# -------------------------------------
# WebSockets
# -------------------------------------

@app.websocket("/app/{app_id}")
async def apps_websocket_endpoint(websocket: WebSocket, app_id: str):
  await websocket.accept()
  client, app = core.get_client_app_by_id(app_id)

  if not client or not app:
    await websocket.close(reason="Unauthorized")
    return

  app.connect_websocket(websocket)
  await app.send_event("connected", {
    "config": app.config.model_dump(),
    "settings": client.user.settings()
  })

  logger.info(f"WebSocket: App connected {app.id} (Client: {client.id})")

  try:
    while True:
      data = await websocket.receive_json()
      logger.debug(f"WebSocket Data (App {app.id}): {data}")
      await core.on_app_data(client, app, data)
  except WebSocketDisconnect:
    logger.info(f"WebSocket: App disconnected {app.id}")
    await core.on_app_disconnect(client, app)
  except Exception as e:
    logger.exception(f"WebSocket Error (App {app.id}): {e}")
    if not is_websocket_connected(websocket):
      return

@app.websocket("/client")
async def websocket_client_endpoint(websocket: WebSocket, access_token: str = Cookie(None)):
  await websocket.accept()
  try:
    user_config = core.auth.get_user(access_token)
    if user_config.username != core.user.username:
      raise Exception("Invalid user")

    client = Client(core.user, core.config.resolve_path, websocket)
    core.clients[client.id] = client
  except Exception:
    await websocket.close(reason="Unauthorized")
    return

  logger.info(f"WebSocket: Client connected {client.id}")
  await client.send_event("connected", {
    "client_id": client.id,
    "settings": client.user.settings()
  })
  
  try:
    while True:
      await websocket.receive_json()
  except WebSocketDisconnect:
    logger.info("WebSocket: Client disconnected")
    await core.on_client_disconnect(client)
  except Exception as e:
    logger.exception(f"WebSocket client error: {e}")
    if not is_websocket_connected(websocket):
      return

# -------------------------------------
# Final plugin hook
# -------------------------------------

core.plugins.after_startup(KikxPlugin(core, app))
