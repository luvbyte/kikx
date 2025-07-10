from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Any
import os
import shutil
from pathlib import Path
import httpx
import mimetypes

from urllib.parse import urlparse
from lib.service import create_service


srv = create_service(__file__)

class FileWriteRequest(BaseModel):
  filename: str
  content: str

class DirectoryCreateRequest(BaseModel):
  dirname: str

class CopyMoveRequest(BaseModel):
  source: str
  destination: str


def resolve_app_path(app, path: str, read: bool):
  core = srv.get_core()
  
  try:
    protocol, full_path = path.split("://", 1)
  except ValueError:
    protocol = "data"
    full_path = path
    #raise HTTPException(status_code=400, detail="Invalid path protocol")

  protocol_paths = {
    "file": app.get_app_path(),
    "data": app.get_app_data_path(),
    "home": app.get_home_path()
  }
  # special access
  if protocol == "root":
    permission = "storage.read_root" if read else "storage.write_root"
    if not app.has_permission(permission):
      srv.exception(403, "Permission denied")
    return core.config.resolve_path(full_path)
  
  if protocol not in protocol_paths:
    srv.exception(400, "Invalid path protocol")
  
  # maybe remove in future
  elif protocol == "file" and not read:
    raise HTTPException(status_code=403, detail="Permission denied can't write to file://")
  elif protocol == "home":
    permission = "storage.read_home" if read else "storage.write_home"
    if not app.has_permission(permission):
      srv.exception(403, "Permission denied")

  return protocol_paths[protocol] / full_path

def resolve_client_path(client, path: str):
  core = srv.get_core()
  # full files access implement permissions later
  return core.config.resolve_path(path)

def resolve_path(request: Request, path: str, read: bool = False) -> Path:
  """Resolve a given path based on protocol type and request context."""
  client, app = srv.get_client_or_app(request)
  if app:
    return resolve_app_path(app, path, read)
  else:
    return resolve_client_path(client, path)


# implement something like this in core
@srv.router.get("/map")
def path_map(request: Request, path: str):
  return {
    "apps": "storage://apps"
  }[path]

@srv.router.post("/copy")
def copy_item(request: Request, payload: CopyMoveRequest):
  """Copy a file or directory from source to destination."""
  src_path = resolve_path(request, payload.source, True)
  dest_path = resolve_path(request, payload.destination)

  if not os.path.exists(src_path):
    raise HTTPException(status_code=404, detail="Source not found")

  if os.path.isdir(src_path):
    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
  else:
    shutil.copy2(src_path, dest_path)

  return {"message": "Copy successful", "source": payload.source, "destination": payload.destination}

@srv.router.post("/move")
def move_item(request: Request, payload: CopyMoveRequest):
  """Move (rename) a file or directory from source to destination."""
  src_path = resolve_path(request, payload.source)
  dest_path = resolve_path(request, payload.destination)

  if not os.path.exists(src_path):
    raise HTTPException(status_code=404, detail="Source not found")

  shutil.move(src_path, dest_path)

  return {"message": "Move successful", "source": payload.source, "destination": payload.destination}

@srv.router.get("/list", response_model=List[Any])
def list_files(request: Request, directory: str = ""):
  """List files and directories inside a given directory."""
  dir_path = resolve_path(request, directory, True)

  if not os.path.exists(dir_path):
    raise HTTPException(status_code=404, detail="Directory not found")
  
  def file_info(path):
    return {
      "name": path.name,
      "suffix": path.suffix,
      "directory": path.is_dir()
    }

  return [file_info(Path(dir_path) / path) for path in os.listdir(dir_path)]

@srv.router.get("/read")
def read_file(request: Request, filename: str):
  """Read a file efficiently using streaming."""
  file_path = resolve_path(request, filename, True)

  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")

  def file_generator():
    with open(file_path, "rb") as file:
      while chunk := file.read(1024 * 1024):  # Read in 1MB chunks
        yield chunk

  return StreamingResponse(file_generator(), media_type="application/octet-stream")

@srv.router.post("/write")
def write_file(request: Request, file: FileWriteRequest):
  """Write content to a file."""
  file_path = resolve_path(request, file.filename)
  
  with open(file_path, "w", encoding="utf-8") as f:
    f.write(file.content)

  return {"message": "File written successfully", "filename": file.filename}

@srv.router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
  """Upload a file efficiently by writing in chunks."""
  file_path = resolve_path(request, file.filename)

  with open(file_path, "wb") as f:
    while chunk := await file.read(1024 * 1024):  # Read in 1MB chunks
      f.write(chunk)

  return {"message": "File uploaded successfully", "filename": file.filename}

@srv.router.delete("/delete")
def delete_file(request: Request, filename: str):
  """Delete a file."""
  file_path = resolve_path(request, filename)

  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")

  os.remove(file_path)
  return {"message": "File deleted successfully"}

@srv.router.post("/create_directory")
def create_directory(request: Request, dir_request: DirectoryCreateRequest):
  """Create a new directory."""
  dir_path = resolve_path(request, dir_request.dirname)

  if os.path.exists(dir_path):
    raise HTTPException(status_code=400, detail="Directory already exists")

  os.makedirs(dir_path)
  return {"message": "Directory created successfully"}

@srv.router.delete("/delete_directory")
def delete_directory(request: Request, dirname: str):
  """Delete a directory and its contents."""
  dir_path = resolve_path(request, dirname)

  if not os.path.exists(dir_path):
    raise HTTPException(status_code=404, detail="Directory not found")

  shutil.rmtree(dir_path)
  return {"message": "Directory deleted successfully"}

# remove (deprecated)
@srv.router.get("/serve")
async def serve_file(request: Request, filename: str):
  """Serve a locally saved file for downloading."""
  file_path = resolve_path(request, filename, True)

  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")

  return StreamingResponse(
    open(file_path, "rb"),
    media_type="application/octet-stream",
    headers={"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
  )
