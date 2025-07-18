import os
import shutil
import logging
from pathlib import Path
from typing import List, Any

from fastapi import (
  APIRouter, HTTPException, Request,
  UploadFile, File, Query
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lib.service import create_service

srv = create_service(__file__)
logger = logging.getLogger("storage")
logging.basicConfig(level=logging.INFO)

class FileWriteRequest(BaseModel):
  filename: str
  content: str

class DirectoryCreateRequest(BaseModel):
  dirname: str

class CopyMoveRequest(BaseModel):
  source: str
  destination: str


def resolve_app_path(app, path: str, read: bool) -> Path:
  core = srv.get_core()
  if "://" in path:
    protocol, full_path = path.split("://", 1)
  else:
    protocol, full_path = "data", path

  ptype = "read" if read else "write"
  permissions = app.get_permissions("storage")

  if protocol == "data":
    return app.get_app_data_path() / full_path

  if protocol == "root":
    if permissions.check("root", ptype):
      return core.config.resolve_path(full_path)
    else:
      srv.exception(400, "Permission denied for root access")

  storage_paths = {
    "app": app.get_app_path(),
    "home": app.get_home_path()
  }

  if protocol not in storage_paths:
    srv.exception(400, "Invalid protocol")

  if not permissions.check(protocol, ptype):
    srv.exception(400, "Permission denied")

  return storage_paths[protocol] / full_path


def resolve_client_path(client, path: str) -> Path:
  core = srv.get_core()
  return core.config.resolve_path(path)


def resolve_path(request: Request, path: str, read: bool = False) -> Path:
  """Resolve a given path based on protocol and auth context."""
  client, app = srv.get_client_or_app(request)
  return resolve_app_path(app, path, read) if app else resolve_client_path(client, path)


@srv.router.post("/copy")
def copy_item(request: Request, payload: CopyMoveRequest) -> dict:
  src_path = resolve_path(request, payload.source, True)
  dest_path = resolve_path(request, payload.destination)

  if not os.path.exists(src_path):
    raise HTTPException(status_code=404, detail="Source not found")

  if os.path.isdir(src_path):
    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
  else:
    shutil.copy2(src_path, dest_path)

  logger.info(f"Copied from {src_path} to {dest_path}")
  return {"message": "Copy successful", "source": payload.source, "destination": payload.destination}


@srv.router.post("/move")
def move_item(request: Request, payload: CopyMoveRequest) -> dict:
  src_path = resolve_path(request, payload.source)
  dest_path = resolve_path(request, payload.destination)

  if not os.path.exists(src_path):
    raise HTTPException(status_code=404, detail="Source not found")

  shutil.move(src_path, dest_path)
  logger.info(f"Moved from {src_path} to {dest_path}")
  return {"message": "Move successful", "source": payload.source, "destination": payload.destination}


@srv.router.get("/list", response_model=List[Any])
def list_files(request: Request, directory: str = "") -> List[dict]:
  dir_path = resolve_path(request, directory, True)

  if not os.path.exists(dir_path):
    raise HTTPException(status_code=404, detail="Directory not found")

  def file_info(path: Path) -> dict:
    return {
      "name": path.name,
      "suffix": path.suffix,
      "directory": path.is_dir()
    }

  return [file_info(Path(dir_path) / path) for path in os.listdir(dir_path)]


@srv.router.get("/read")
def read_file(request: Request, filename: str) -> StreamingResponse:
  file_path = resolve_path(request, filename, True)

  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")

  def file_generator():
    with open(file_path, "rb") as file:
      while chunk := file.read(1024 * 1024):
        yield chunk

  return StreamingResponse(file_generator(), media_type="application/octet-stream")


@srv.router.post("/write")
def write_file(request: Request, file: FileWriteRequest) -> dict:
  file_path = resolve_path(request, file.filename)

  with open(file_path, "w", encoding="utf-8") as f:
    f.write(file.content)

  logger.info(f"Wrote to file {file_path}")
  return {"message": "File written successfully", "filename": file.filename}


@srv.router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)) -> dict:
  file_path = resolve_path(request, file.filename)

  with open(file_path, "wb") as f:
    while chunk := await file.read(1024 * 1024):
      f.write(chunk)

  logger.info(f"Uploaded file to {file_path}")
  return {"message": "File uploaded successfully", "filename": file.filename}


@srv.router.delete("/delete")
def delete_file(request: Request, filename: str) -> dict:
  file_path = resolve_path(request, filename)

  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")

  os.remove(file_path)
  logger.info(f"Deleted file {file_path}")
  return {"message": "File deleted successfully"}


@srv.router.post("/create_directory")
def create_directory(request: Request, dir_request: DirectoryCreateRequest) -> dict:
  dir_path = resolve_path(request, dir_request.dirname)

  if os.path.exists(dir_path):
    raise HTTPException(status_code=400, detail="Directory already exists")

  os.makedirs(dir_path)
  logger.info(f"Created directory {dir_path}")
  return {"message": "Directory created successfully"}


@srv.router.delete("/delete_directory")
def delete_directory(request: Request, dirname: str) -> dict:
  dir_path = resolve_path(request, dirname)

  if not os.path.exists(dir_path):
    raise HTTPException(status_code=404, detail="Directory not found")

  shutil.rmtree(dir_path)
  logger.info(f"Deleted directory {dir_path}")
  return {"message": "Directory deleted successfully"}


@srv.router.get("/serve")
async def serve_file(request: Request, filename: str) -> StreamingResponse:
  """Deprecated: Serve a file for download."""
  file_path = resolve_path(request, filename, True)

  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")

  return StreamingResponse(
    open(file_path, "rb"),
    media_type="application/octet-stream",
    headers={"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
  )
