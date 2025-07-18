import os
import shutil
from pathlib import Path
from uuid import uuid4
from typing import List, Any

from fastapi import (
  Request, File, UploadFile, HTTPException
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from lib.parser import parse_config
from lib.service import create_service

srv = create_service(__file__)

class Config(BaseModel):
  storage: str = Field(..., description="Storage path")

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

class VI:
  def __init__(self, config_file: Path):
    self.config: Config = parse_config(config_file, Config)

  def init(self, core: Any) -> None:
    self.config.storage = core.config.resolve_path(self.config.storage)

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

# Serve static files from www folder
@srv.router.get("/{path:path}")
def home(path: str):
  path = "index.html" if not path else path
  file = vi.config.home_path / path
  if file.is_dir() or not file.exists():
    srv.exception(404, "File not found")
  return FileResponse(file)
