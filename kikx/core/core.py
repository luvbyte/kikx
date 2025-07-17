# Optimized & Improved Code
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, Request, Response, Depends, Cookie, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from fastapi.staticfiles import StaticFiles

from fastapi.security import OAuth2PasswordRequestForm

from core.plugins import PluginsManager

from pydantic import BaseModel
from subprocess import Popen
from pathlib import Path
from uuid import uuid4

import logging
import asyncio
import signal
import shlex
import json
import sys
import os

from typing import Dict, List

from lib.utils import dynamic_import, is_websocket_connected

from core.config import Config

from core.storage import Storage
from core.errors import raise_error, Error, ClientError, AppError, TaskError

from core.auth import Auth
# from core.apps import App

from lib.plugins import KikxPlugin

from core.models import CloseAppModel, OpenAppModel, AppsListModel
from core.services import Services
from lib.parser import parse_config

from core.shortlink import ShortLink
# from lib.utils import is_websocket_connected
from core.config.models import UserModel, AppModel, UserDataModel

from core.client import Client
from core.user import User

import subprocess
#from core.global_config import global_config
#from weakref import WeakValueDictionary
#from core.clients import Client, User
# -------------------------------------
# Logging Configuration
# -------------------------------------
logging.basicConfig(level=logging.INFO, format="\n%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Note create seperate files for User, Client
# -------------------------------------
# Core API
# -------------------------------------

# client 
class Core:
  def __init__(self):
    print("\n<===[ CORE INIT ]===>\n")
    
    self.config = Config("../storage")
    # run boot file
    boot_file = self.config.resolve_path("storage://etc/boot.sh")
    if boot_file.exists() and not boot_file.is_dir():
      subprocess.Popen(f"chmod +x {boot_file} && {boot_file}", shell=True, stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr).wait()

    self.plugins = PluginsManager(self.config.kikx.plugins)
    self.services = Services(self.config.resolve_path("storage://config/services.json"))
    self.auth = Auth(self.config.resolve_path("storage://config/auth.json"))
    
    self.user = User(
      self.auth.user_config,
      self.config.resolve_path("data://"),
      self.config.resolve_path("home://"),
      self.config.resolve_path("storage://")
    )
    self.shortlink = ShortLink(self.config.resolve_path("storage://shortlinks"))

    self.clients: Dict[str, Client] = {}
    # app index
    # app_id: ( client, app ) <-> for faster lookups
    # now app_id: client_id
    self.app_index = {}
  
  def get_client(self, client_id):
    return self.clients.get(client_id)

  def get_client_app_by_id(self, app_id: str):
    client_id = self.app_index.get(app_id)  # O(1) lookup for client_id
    if client_id is None:
      return None, None  # App not found

    client = self.clients.get(client_id)  # O(1) lookup for client
    if client is None:
      return None, None  # Client not found (stale entry)

    app = client.running_apps.get(app_id)  # O(1) lookup for app
    return (client, app) if app else (None, None)  # Return (client, app) or (None, None)

  # --------------------------- Apps
  def open_app(self, client_id: str, name):
    # get client 
    client = self.clients.get(client_id)
    if client is None:
      raise_error("client not found")

    app = client.open_app(name)
    self.app_index[app.id] = client.id
    return app

  # closes app & delets in running_list
  async def close_app(self, client, app):
    await client.close_app(app)
    del self.app_index[app.id]
    
    print("App Index", self.app_index)

  async def on_app_data(client, app, data):
    pass

  # on js close
  async def on_app_disconnect(self, client, app):
    pass
  # --------------- client
  # on client ws close
  async def on_client_disconnect(self, client):
    # Close all running apps for the client
    for app_id in list(client.running_apps.keys()):  # Create a list to avoid modifying while iterating
      self.app_index.pop(app_id, None)  # Remove app from index
    # Close the client connection
    await client.on_close()
    # Remove the client
    del self.clients[client.id]
    # finally closing & removing client 

    logger.info(f"Client closed {client}")
    logger.info(f"Active clients {self.clients}")
    logger.info(f"App Index List : {self.app_index}")
  
  # on before fastapi start
  async def on_start(self):
    pass
  
  # on before fastapi stop
  async def on_close(self):
    self.plugins.shutdown()
    self.services.on_close()
    
    shutdown_file = self.config.resolve_path("storage://etc/shutdown.sh")
    if shutdown_file.exists() and not shutdown_file.is_dir():
      subprocess.Popen(f"chmod +x {shutdown_file} && {shutdown_file}", shell=True, stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr).wait()


#  core
core = Core()

# lifespan 
async def lifespan(self):
  await core.on_start()
  print("<=== [ KIKX STARED ] ===>")  # Initialization logic
  yield
  await core.on_close()
  print("<=== [ KIKX CLOSED ] ===>")  # Initialization logic


# router fastapi server
app = FastAPI(lifespan = lifespan)
# app.state.core = core

core.plugins.load(core)

# before load
core.plugins.before_startup(KikxPlugin(core, app))
# loading services
core.services.load(core, app)
# loading plugins

#@app.exception_handler(Exception)
#async def global_exception_handler(request, exc):
#  return JSONResponse(
#    status_code=500,
#    content={"detail": "Internal Server Error"},
#  )


api = APIRouter()


origins = [
  "null", "*"
]
# loading plugins

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.mount("/share", StaticFiles(directory=core.config.share_path), name="share")
app.mount("/files", StaticFiles(directory=core.config.files_path), name="files")

# ----------------api routes
class AppManifestModel(BaseModel):
  title: str
  icon: str
  category: str | None = None

@api.post("/apps/list")
def get_apps_list(data: AppsListModel, category: str | None = None):
  client = core.clients.get(data.client_id)
  if client is None:
    raise HTTPException(status_code=401, detail="Client not found")

  installed_apps = client.user.get_installed_apps()  # Remove duplicates

  # use icon sets here
  def get_app_icon_path(name, icon):
    # checking icon modification
    icons_path = core.config.resolve_path("share://icons/app") / f"{name}.png"
    # icon ovveriding
    if icons_path.exists() and not icons_path.is_dir():
      return f"/share/icons/app/{name}.png"
    return f'/public/app/{name}/{icon}'

  def load_manifest(name):
    app_path =  core.config.apps_path / name / "app.json"
    if not app_path.exists():
      return None  # Skip missing files

    try:
      app_manifest = parse_config(app_path, AppManifestModel)
      # check sorting conditions here
      if category and category.lower() != app_manifest.category.lower():
        return None
      # Directly access required fields (KeyError will be raised if missing)
      return {
        "name": name,
        "title": app_manifest.title,
        "icon": get_app_icon_path(name, app_manifest.icon),
        #"icon": f'/public/app/{name}/{app_manifest.icon}',
      }
    except Exception:
      return None  # Skip corrupted or incomplete files

  return [app for app in map(load_manifest, installed_apps) if app]

# command api
# ---------------
app.include_router(api, prefix="/api", tags=["Api"])

# --------------- app routes
@app.get("/login", tags=["Auth"])
def login_page():
  return FileResponse("www/auth/login.html")

@app.post("/login", tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
  user = core.auth.authenticate_user(form_data.username, form_data.password)
  if user is None:
    raise HTTPException(status_code=401, detail={"detail": "Invalid credentials"})
    #return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

  token = core.auth.create_access_token(data={"sub": user})
  response = JSONResponse(content={"message": "Login successful"})
  #response.set_cookie(key="access_token", value=token, samesite="strict", httponly=True, secure=True)  # Store JWT in cookies
  response.set_cookie(key="access_token", value=token, samesite="strict", httponly=True)  # Store JWT in cookies
    
  return response

@app.get("/logout", tags=["Auth"])
def logout():
  """Clears username, user_hash cookies"""
  response = RedirectResponse("/")
  response.delete_cookie("access_token")
  return response

@app.post("/close-app")
async def close_app(app_model: CloseAppModel):
  client, app = core.get_client_app_by_id(app_model.app_id)
  if client is None or app is None:
    raise HTTPException(status_code=401, detail="Unauthorized")
  try:
    await core.close_app(client, app)
    return { "res": "ok" }
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Cant close app - {e}")

@app.post("/open-app")
def open_app(app_model: OpenAppModel):
  try:
    app = core.open_app(app_model.client_id, app_model.name)
  except Exception as e:
    raise HTTPException(status_code=401, detail=str(e))

  return {
    "id": app.id,
    "url": f"/app/{app.id}/index.html?starting=true",
    "iframe": app.config.iframe
  }

# app files app-id route
@app.get("/app/{app_id}/{path:path}")
async def app_web(app_id: str, path: str, starting: bool = False):
  client, app = core.get_client_app_by_id(app_id)
  if client is None or app is None:
    raise HTTPException(status_code=401, detail="App not found")

  # !test
  if path.startswith("_app/"):  # can access app root folder files
    file = app.app_path / path.replace("_app/", "")
  else:
    file = app.app_path / "www" / path
  
  if not file.exists():
    raise HTTPException(status_code=404, detail="File not found")

  response = FileResponse(file)
  # in dev
  #response.headers.update({
  #  "Cache-Control": "no-cache, no-store, must-revalidate",
  #  "Pragma": "no-cache",
  #  "Expires": "0"
  #})
  return response

@app.get("/public/app/{name}/{path:path}")
async def app_public(name: str, path: str):
  file = core.config.apps_path / name / "public" / path

  if not file.exists():
    raise HTTPException(status_code=404, detail="File not found")

  response = FileResponse(file)
  #response.headers.update({
  #  "Cache-Control": "no-cache, no-store, must-revalidate",
  #  "Pragma": "no-cache",
  #  "Expires": "0"
  #})
  return response

# can use different launchers on different platform
# need testing
@app.get("/ui/{ui_name}/{path:path}")
def home_page(request: Request, ui_name: str, path: str):
  token = request.cookies.get("access_token")
  
  ui_config = core.config.kikx.ui.get(ui_name)
  if ui_config is None:
    raise HTTPException(status_code=404, detail="UI config not found")

  # setting None to generate in cookie
  token = core.auth.check_token(token)

  if ui_config.require_auth and token is None:
    return RedirectResponse("/login")

  # check if user has that ui enabled
  user_config = core.auth.user_config
  if ui_name not in user_config.ui:
    raise HTTPException(status_code=404, detail="UI not found")

  if len(path.strip()) == 0:
    path = "index.html"

  file_path = core.config.resolve_path(ui_config.path) / "www" / path

  if not file_path.exists() or file_path.is_dir():
    raise HTTPException(status_code=404, detail="File not found")

  response = FileResponse(file_path)
  
  if token is None:
    response.set_cookie(key="access_token", value=core.auth.generate_access_token(), samesite="strict", httponly=True)  # Store JWT in cookies
  
  return response

@app.get("/sl/{path:path}")
def redirect(path: str):  # shortlinks
  try:
    return RedirectResponse(core.shortlink.resolve(path))
  except Exception as e:
    raise HTTPException(status_code=404, detail=str(e))

@app.get("/")
def root_page(request: Request):
  # set csrf token here
  return RedirectResponse("/ui/" + core.auth.user_config.default_ui)

# --------------- websockets
@app.websocket("/app/{app_id}")
async def apps_websocket_endpoint(websocket: WebSocket, app_id: str):
  await websocket.accept()

  # start error checking from here
  client, app = core.get_client_app_by_id(app_id)
  if app is None or client is None:
    await websocket.close(reason="Unauthorized")
    return
  
  # safe functions
  app.connect_websocket(websocket)
  await app.send_event("connected", { "config": app.config.model_dump(), "settings": client.user.settings.parsed })
  
  logger.info(f"App opened {app} ∆ client : {client}")
  logger.info(f"Active apps {client.running_apps}")

  try:
    while True:
      data = await websocket.receive_json()
      print("Got app data :", data)
      await core.on_app_data(client, app, data)
  except WebSocketDisconnect:
    await core.on_app_disconnect(client, app)
  except Exception as e:
    logger.exception(f"Got exception on handling app data : {e}")
    # returning if dusconnected
    if not is_websocket_connected(websocket):
      return

@app.websocket("/client")
async def websocket_client_endpoint(websocket: WebSocket, access_token: str = Cookie(None)):
  await websocket.accept()
  
  try:
    # make apps path different for user in future
    user_config = core.auth.get_user(access_token)
    if user_config.username != core.user.username:
      raise Exception("Invalid user")
    
    client = Client(core.user, core.config.resolve_path, websocket)
    core.clients[client.id] = client
    # --------------6
  except Exception as e:
    print("Client connect error : ", e)
    await websocket.close(reason=str(e))
    return

  logger.info(f"Client created {client}")
  logger.info(f"Active clients {core.clients}")

  # changing here
  await client.send_event("connected", {
    "client_id": client.id,
    "settings": client.user.settings.parsed
  })

  try:
    while True:
      _ = await websocket.receive_json()
  except WebSocketDisconnect:
    await core.on_client_disconnect(client)
  except Exception as e:
    logger.exception(f"Got exception on handling app data : {e}")
    # returning if dusconnected
    if not is_websocket_connected(websocket):
      return

# make in on_startup
core.plugins.after_startup(KikxPlugin(core, app))
