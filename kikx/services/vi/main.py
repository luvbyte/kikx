from fastapi import Request, File, UploadFile, Header, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from pydantic import BaseModel, Field
import shutil
from uuid import uuid4
from typing import Dict, List, Any
import os

from lib.parser import parse_config
from lib.service import create_service


srv = create_service(__file__)

class Config(BaseModel):
  storage: str = Field(..., description="Storage path")
  
  def create_dirs(self, path):
    os.makedirs(path, exist_ok=True)
    return Path(path)

  @property
  def storage_path(self):
    return self.create_dirs(self.storage).resolve()

  @property
  def home_path(self):
    return srv.path / "www"

  @property
  def data_path(self):
    return self.create_dirs(self.storage_path / "uploads" / "data")
  
  @property
  def meta_path(self):
    return self.create_dirs(self.storage_path / "uploads" / "meta")

class VI:
  def __init__(self, config_file):
    self.config = parse_config(config_file, Config)
  
  def init(self, core):
    self.config.storage = core.config.resolve_path(self.config.storage)

vi = VI(srv.path / "config.json")

@srv.on("load")
def on_load():
  vi.init(srv.kikx_core)

# files upload
@srv.router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
  filename = f"{uuid4().hex}__{file.filename}"
  contents = await file.read()
  with open(vi.config.data_path / filename, "wb") as f:
    f.write(contents)
  return {
    "filename": filename
  }

# assuming config.data_path is a Path object
@srv.router.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
  uploaded_files = []
  for file in files:
    filename = f"{uuid4().hex}__{file.filename}"
    file_path = vi.config.data_path / filename
    with open(file_path, "wb") as f:
      shutil.copyfileobj(file.file, f)
      uploaded_files.append(filename)
  return { "files_meta": uploaded_files }

# upload multiple files at a time
@srv.router.post("/upload-meta")
async def upload_meta(request: Request):
  data = await request.body()
  content_type = request.headers.get("Content-Type")
  if content_type == "application/json":
    with open(vi.config.meta_path / f"{uuid4().hex}__meta.json", "wb") as file:
      file.write(data)
  else:
    with open(vi.config.meta_path / f"{uuid4().hex}__meta.txt", "wb") as file:
      file.write(data)

# www server
@srv.router.get("/{path:path}")
def home(path: str):
  path = "index.html" if len(path) <= 0 else path
  file = vi.config.home_path / path
  if file.is_dir() or not file.exists():
    srv.exception(404, "File not found")
  return FileResponse(file)


