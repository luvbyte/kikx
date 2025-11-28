import os
import shutil
import asyncio
from uuid import uuid4
from pathlib import Path
from typing import List, Any

from fastapi import (
  Request, WebSocket, WebSocketDisconnect, File, UploadFile, HTTPException
)
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from lib.parser import parse_config
from lib.service import create_service
from lib.utils import is_websocket_connected

srv = create_service(__file__)

class Config(BaseModel):
  storage: str = Field(..., description="Storage path")
  scripts: str = Field(..., description="Scripts path")
  key: str = Field(..., description="Admin key")

  def create_dirs(self, path: Path) -> Path:
    os.makedirs(path, exist_ok=True)
    return Path(path)

  @property
  def storage_path(self) -> Path:
    return self.create_dirs(self.storage).resolve()

  @property
  def home_path(self) -> Path:
    return srv.path / "www"

  @property
  def data_path(self) -> Path:
    return self.create_dirs(self.storage_path / "uploads" / "data")

  @property
  def meta_path(self) -> Path:
    return self.create_dirs(self.storage_path / "uploads" / "meta")
  
  @property
  def scripts_path(self) -> Path:
    return self.create_dirs(self.scripts).resolve()

  def check_key(self, key) -> bool:
    return key == self.key


class Events:
  def __init__(self):
    # Store event_name -> list of async handler functions
    self._events = {}

  def bind(self, event_name, func):
    """Bind an async function to an event."""
    if not asyncio.iscoroutinefunction(func):
      raise TypeError("Bound function must be async")
    self._events.setdefault(event_name, []).append(func)

  def unbind(self, event_name, func=None):
    """Unbind one or all functions from an event."""
    if event_name in self._events:
      if func:
        self._events[event_name] = [
          f for f in self._events[event_name] if f != func
        ]
        if not self._events[event_name]:
          del self._events[event_name]
      else:
        del self._events[event_name]

  async def emit(self, event_name, *args, **kwargs):
    """Call all async functions bound to an event."""
    if event_name not in self._events:
      return

    tasks = []
    for func in self._events[event_name]:
      tasks.append(asyncio.create_task(func(*args, **kwargs)))

    # Run all handlers concurrently and wait for them to complete
    await asyncio.gather(*tasks, return_exceptions=True)

# -> event: exec, payload: whoami, id: someid
# <- event: exec, id: someid, returnCode: 0, stdout: 'gojo\n', stderr: ''

class Client:
  def __init__(self, ws, sclient=False, name: str = ""):
    self.ws = ws
    self.cid = uuid4().hex

    self.sclient = sclient
    
    self.name = name
  
    self._meta = {
      "cid": self.cid
    }

  @property
  def is_sclient(self):
    return self.sclient
  
  @property
  def meta(self):
    return {
      "cid": self.cid,
      "name": self.name
    }
  
  async def send_json(self, data):
    if not is_websocket_connected(self.ws):
      return 
    await self.ws.send_json(data)
  
  async def send_event(self, event, payload, **kwargs):
    # TODO: check if connected state
    await self.send_json({
      "event": event, "payload": payload, **kwargs
    })

  async def send_error(self, code, detail):
    # TODO: check if connected state
    await self.send_event("error", {
      "code": code, "detail": detail
    })

class Clients:
  def __init__(self):
    self.events = Events()

    self.clients = {}
    self.sclients = {}

  async def on_connect(self, websocket, sclient=False, name: str = ""):
    client = Client(websocket, sclient=sclient, name=name)
    if sclient:
      self.sclients[client.cid] = client
      # emiting event connected
      await client.send_event("connected", { cid: client.meta for cid, client in self.clients.items() })
    else:
      self.clients[client.cid] = client
      # broadcast to sclients
      for sc in self.sclients.values():
        await sc.send_event("client:connected", client.meta)
    return client

  async def on_data(self, client, data):
    print(f"data: S? {client.is_sclient}", data)
    try:
      event = data["event"]
      # if its exec event
      if event == "exec":
        # if coming from sclient
        if client.is_sclient:
          payload = data["payload"]
          await self.clients.get(payload["cid"]).send_json({
            "event": "exec", "payload": payload["command"], "id": f"{client.cid}_{payload['id']}"
          })
        else:
          sclient_id, rid = data["id"].split("_", 1)
          await self.sclients[sclient_id].send_json({
              "event": "exec", "id": rid, "payload": {
                "stdout": data["stdout"],
                "stderr": data["stderr"],
                "returncode": data["returnCode"]
              }
            })
    except Exception as e:
      # TODO: remove later
      raise e
  
  async def on_disconnect(self, client):
    if client.sclient:
      self.sclients.pop(client.cid)
    else:
      # broadcast to sclients
      for sc in self.sclients.values():
        await sc.send_event("client:disconnected", client.cid)
      self.clients.pop(client.cid)

class VI:
  def __init__(self, config_file: Path):
    self.config: Config = parse_config(config_file, Config)
    self.clients: Clients = Clients()
  
  # on service start
  def init(self, core: Any) -> None:
    self.config.storage = core.config.resolve_path(self.config.storage)
    self.config.scripts = core.config.resolve_path(self.config.scripts)


vi = VI(srv.path / "config.json")

@srv.on("load")
def on_load() -> None:
  vi.init(srv.get_core())

# Upload a single file
@srv.router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
  filename = f"{uuid4().hex}__{file.filename}"
  contents = await file.read()
  with open(vi.config.data_path / filename, "wb") as f:
    f.write(contents)
  return { "filename": filename }

# Upload multiple files
@srv.router.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)) -> dict:
  uploaded_files: List[str] = []
  for file in files:
    filename = f"{uuid4().hex}__{file.filename}"
    file_path = vi.config.data_path / filename
    with open(file_path, "wb") as f:
      shutil.copyfileobj(file.file, f)
    uploaded_files.append(filename)
  return { "files_meta": uploaded_files }

# Upload metadata (as JSON or plain text)
@srv.router.post("/upload-meta")
async def upload_meta(request: Request) -> None:
  data = await request.body()
  content_type = request.headers.get("Content-Type", "")
  ext = "json" if content_type == "application/json" else "txt"
  meta_file = vi.config.meta_path / f"{uuid4().hex}__meta.{ext}"
  with open(meta_file, "wb") as f:
    f.write(data)

# --------- +++++
@srv.router.get("/list-scripts/{path:path}")
def list_scripts(path: str, key: str):
  if key != vi.config.key:
    raise HTTPException(status_code=400, detail="forbidden")
  
  root = (vi.config.scripts_path / path).resolve()
  def script_meta(directory):
    return {
      "name": directory.with_suffix("").name,
      "path": directory.relative_to(vi.config.scripts_path).as_posix(),
      "isdir": directory.is_dir(),
      "ext": directory.suffix
    }

  # if the OS directory itself doesn't exist -> 404
  if not root.is_dir():
    raise HTTPException(status_code=404, detail="Not found")
  try:
    root.relative_to(vi.config.scripts_path)
  except ValueError:
    # requested is outside of root
    raise HTTPException(status_code=403, detail="Forbidden")

  # Build safe listing: return relative POSIX paths (not absolute)
  scripts = [script_meta(path) for path in root.iterdir()]

  return {
    "items": scripts,
    "path": path
  }

@srv.router.get("/script/{path:path}")
def script(path: str, key: str):
  if key != vi.config.key:
    raise HTTPException(status_code=400, detail="forbidden")

  root = (vi.config.scripts_path / path).resolve()
  if root.is_dir():
    raise HTTPException(status_code=404, detail="File not found")
  try:
    root.relative_to(vi.config.scripts_path)
  except ValueError:
    # requested is outside of root
    raise HTTPException(status_code=403, detail="Forbidden")
  
  return FileResponse(root)

@srv.router.get("/app-access")
def app_access(request: Request):
  srv.get_client_or_app(request)
  return { 
    "key": vi.config.key,
    "url": f"/service/vi/admin/index.html?key={vi.config.key}"
  }

# Serve static files from www folder (safe)
@srv.router.get("/{path:path}")
def home(path: str):
  base_path = Path(vi.config.home_path).resolve()
  requested_path = base_path / (path or "index.html")

  try:
    resolved_path = requested_path.resolve(strict=False)
  except Exception:
    raise HTTPException(status_code=404, detail="Invalid path")

  # Ensure the file is within the base directory
  if not str(resolved_path).startswith(str(base_path)):
    raise HTTPException(status_code=403, detail="Access denied")

  if not resolved_path.exists() or resolved_path.is_dir():
    raise HTTPException(status_code=404, detail="File not found")

  return FileResponse(resolved_path)


# --------- +++++ ws
@srv.router.websocket("/client/{name}")
async def client_websocket_endpoint(websocket: WebSocket, name: str):
  await websocket.accept()
  # add try, exec
  client = await vi.clients.on_connect(websocket, sclient=False, name=name)
  try:
    while True:
      data = await websocket.receive_json()
      await vi.clients.on_data(client, data)
  except WebSocketDisconnect:
    await vi.clients.on_disconnect(client)
  except Exception as e:
    print(e)


@srv.router.websocket("/sclient")
async def super_client_websocket_endpoint(websocket: WebSocket, key: str):
  await websocket.accept()
  # checking key
  if not vi.config.check_key(key):
    await websocket.close(reason="Unauthorized")
    return
  # add try, exec
  sclient = await vi.clients.on_connect(websocket, sclient=True)
  try:
    while True:
      data = await websocket.receive_json()
      await vi.clients.on_data(sclient, data)
  except WebSocketDisconnect:
    await vi.clients.on_disconnect(sclient)
  except Exception as e:
    print(e)

