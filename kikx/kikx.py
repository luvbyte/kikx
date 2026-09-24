import os
import asyncio
import logging

from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from fastapi import (
  FastAPI, WebSocket, WebSocketDisconnect,
  Request, Cookie, HTTPException, Form
)
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.core import Core
from core.logging import setup_logging
from core.global_config import GlobalConfig
from core.models.app import AppOptionsModel

from config.setup import VOLUMES_PATH, STORAGE_NAME

from lib.utils import file_response, import_relative_module


# ---------------------- Logging Configuration

gconfig = GlobalConfig()

STORAGE = (VOLUMES_PATH / STORAGE_NAME).resolve()

if not STORAGE.is_dir():
  raise Exception(f"\nFS path '{STORAGE}' not found!!!\n")

if not (STORAGE / "config/kikx.json").resolve().is_file():
  raise Exception("Invalid kikx storage path")

setup_logging(
  os.path.join(STORAGE, "logs"),
  f"kikx_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

logger = logging.getLogger(__name__)


# ---------------------- Core App Initialization

class KikxApp:
  def __init__(self):
    self.core = Core(STORAGE, dev_mode=gconfig.kikx.dev_mode)

    if self.core.is_dev_mode:
      self.router = FastAPI(lifespan=self.lifespan)
    else:
      self.router = FastAPI(
        lifespan=self.lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None
      )

    self.router.state.core = self.core

    origins = ["*"] if self.core.is_dev_mode else ["null"]

    self.router.add_middleware(
      CORSMiddleware,
      allow_origins=origins,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
    )

    # Static files
    self.router.mount("/share", StaticFiles(directory=self.core.config.share_path), name="share")
    self.router.mount("/files", StaticFiles(directory=self.core.config.files_path), name="files")

  @asynccontextmanager
  async def lifespan(self, app: FastAPI):
    await self.core.on_start(app)

    self.core.scr.title("KIKX STARTED")

    if not self.core.is_dev_mode:
      server_config = self.core.config.server
      self.core.scr.print(f"http://{server_config.host}:{server_config.port}\n")

    yield

    await self.core.on_close()

  async def __call__(self, scope, receive, send):
    await self.router(scope, receive, send)


kikx_app = KikxApp()


# ---------------------- Global exception handler

@kikx_app.router.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
  if request.scope["type"] == "websocket":
    raise exc

  if kikx_app.core.is_dev_mode:
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


# ---------------------- Dynamically loading routes

for file in os.listdir("core/routes"):
  if file.endswith(".py") and file not in ("__init__.py",):
    module_name = file[:-3]

    if module_name == "dev" and not kikx_app.core.is_dev_mode:
      continue

    module = import_relative_module(f"core.routes.{module_name}", module_name)

    if hasattr(module, "router"):
      kikx_app.router.include_router(
        getattr(module, "router"),
        prefix=f"/{module_name}",
        tags=[module_name.capitalize()]
      )


# ---------------------- Models

class CloseAppModel(BaseModel):
  app_id: str = Field(..., description="App ID")
  client_id: str = Field(..., description="Client ID")


class OpenAppModel(BaseModel):
  name: str = Field(..., description="App name")
  client_id: str = Field(..., description="Client ID")
  options: AppOptionsModel = Field(default_factory=AppOptionsModel)


# ---------------------- Auth Routes

@kikx_app.router.get("/login", tags=["Auth"])
def login_page():
  return file_response("web/auth", "login.html")


@kikx_app.router.post("/login", tags=["Auth"])
def login(access: str = Form(...), ui: str = Form(...)):
  if not kikx_app.core.user.is_ui_exists(ui):
    raise HTTPException(404, "UI not found")

  access_token = kikx_app.core.auth.generate_access_token(access, ui)

  response = JSONResponse(content={"message": "Login successful"})
  response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    samesite="strict"
  )

  return response


@kikx_app.router.get("/logout", tags=["Auth"])
def logout():
  response = RedirectResponse("/login")
  response.delete_cookie("access_token")
  return response


# ---------------------- App Lifecycle

@kikx_app.router.post("/open-app")
async def open_app(app_model: OpenAppModel):
  """Open app using name"""
  try:
    app, info = await kikx_app.core.open_app(
      app_model.client_id,
      app_model.name,
      app_model.options
    )

    return {
      "id": app.id,
      "url": f"/app/{app.id}/index.html",
      "iframe": app.config.iframe.get_dict(),
      "splash": app.config.iframe,
      "manifest": info,
      "isSudo": app.is_sudo
    }

  except HTTPException:
    logger.exception(f"Error opening app ({app_model.name})")
    raise
  except Exception as e:
    logger.exception(f"Error opening app ({app_model.name}) {e}")
    raise HTTPException(500, str(e))


@kikx_app.router.post("/close-app")
async def close_app(app_model: CloseAppModel):
  """Close app using app id"""
  try:
    client, app = kikx_app.core.get_client_app_by_id(app_model.app_id)

    if not client or not app:
      raise HTTPException(401, "Unauthorized")

    asyncio.create_task(kikx_app.core.close_app(client, app))

    return {"message": "success"}

  except HTTPException:
    logger.exception(f"Error closing app ({app_model.app_id})")
    raise
  except Exception as e:
    logger.exception(f"Error closing app ({app_model.app_id}) {e}")
    raise HTTPException(500, str(e))


# ---------------------- File Routes

@kikx_app.router.get("/app/{app_id}/{path:path}")
def app_file(app_id: str, path: str, starting: bool = False):
  """Get app file"""
  client, app = kikx_app.core.get_client_app_by_id(app_id)

  if not client or not app:
    raise HTTPException(401, "App not found")

  path = path.replace("_app/", "") if path.startswith("_app/") else f"{app.manifest.web}/{path}"

  return file_response(app.app_path, path)


@kikx_app.router.get("/app-data/{app_id}/{path:path}")
async def app_data_file(app_id: str, path: str, starting: bool = False):
  """Get app data file"""
  client, app = kikx_app.core.get_client_app_by_id(app_id)

  if not client or not app:
    raise HTTPException(401, "App not found")

  return file_response(app.get_app_data_path(), path)


@kikx_app.router.get("/ui/{ui_name}/{path:path}")
def ui_file(request: Request, ui_name: str, path: str, access_token=Cookie(...)):
  """Get ui file"""
  path = "index.html" if not path.strip() else path

  return file_response(kikx_app.core.config.uis_path, ui_name, "www", path)


@kikx_app.router.get("/")
def root_page():
  """Root page redirects to ui"""
  return RedirectResponse("/login")


# ---------------------- WebSockets

@kikx_app.router.websocket("/app/{app_id}")
async def apps_websocket_endpoint(websocket: WebSocket, app_id: str):
  await websocket.accept()

  client, app = kikx_app.core.get_client_app_by_id(app_id)

  try:
    logger.info(f"WebSocket(App) Connect Attempt (ID: {app_id})")

    event_name: str = "reconnected"

    if not client or not app:
      raise PermissionError("Unauthorized")

    if app.connection.new_connection:
      event_name = "connected"

    await app.connect_websocket(websocket)

    await app.send_event(event_name, {})

  except PermissionError as e:
    logger.exception(f"WebSocket(App) Connect Permission Error: {str(e)}")

    try:
      await websocket.close(code=1008, reason=str(e))
    except Exception:
      pass

    return

  except Exception as e:
    logger.exception(f"WebSocket(App) Connect Error: {str(e)}")

    try:
      await websocket.close(reason=str(e))
    except Exception:
      pass

    return

  logger.info(f"WebSocket(App) Connected (App: {app.id}) (Client: {client.id})")

  while True:
    try:
      data = await websocket.receive_json()
      logger.debug(f"WebSocket(App) Data (App {app.id}): {data}")

      await kikx_app.core.on_app_data(client, app, data)

    except WebSocketDisconnect:
      logger.info(f"WebSocket(App) Disconnected (ID: {app.id})")
      break

    except RuntimeError as e:
      logger.exception(f"WebSocket(App) Runtime Error (ID: {app.id}): {e}")
      break

    except Exception as e:
      logger.exception(f"WebSocket(App) Exception (ID: {app.id}): {e}")
      break

  await app.connection.close(websocket)


@kikx_app.router.websocket("/client")
async def websocket_client_endpoint(
  websocket: WebSocket,
  client_id: Optional[str] = None,
  access_token: str = Cookie(None)
):
  await websocket.accept()

  try:
    logger.info(f"WebSocket(Client) Connect Attempt (ID: {client_id}) (Access: {access_token})")

    event_name = "reconnected"

    client = kikx_app.core.get_client(client_id)

    if client is None:
      if kikx_app.core.auth.pop_access_token(access_token) is None:
        raise PermissionError("Unauthorized")

      ui = access_token.split("_")[1]

      client = await kikx_app.core.on_client_connect(access_token, ui)

      event_name = "connected"

    await client.connect_websocket(websocket)

    await client.send_event(event_name, {
      "client_id": client.id
    })

  except PermissionError as e:
    logger.exception(f"WebSocket(Client) Connect Permission Error: {str(e)}")

    try:
      await websocket.close(code=1008, reason=str(e))
    except Exception:
      pass

    return

  except Exception as e:
    logger.exception(f"WebSocket(Client) Connect Error: {str(e)}")

    try:
      await websocket.close(reason=str(e))
    except Exception:
      pass

    return

  logger.info(f"WebSocket(Client) Connected (ID: {client.id})")

  while True:
    try:
      data = await websocket.receive_json()
      logger.debug(f"WebSocket(Client) Data (ID {client.id}): {data}")

      await kikx_app.core.on_client_data(client, data)

    except WebSocketDisconnect:
      logger.info(f"WebSocket(Client) Disconnected (ID: {client.id})")
      break

    except RuntimeError as e:
      logger.exception(f"WebSocket(Client) Runtime Error (ID: {client.id}): {e}")
      break

    except Exception as e:
      logger.exception(f"WebSocket(Client) Exception (ID: {client.id}): {e}")
      break

  await client.connection.close(websocket)