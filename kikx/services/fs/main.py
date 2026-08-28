import os
import stat
import shutil
import logging
import mimetypes

from PIL import Image
from queue import Queue
from pathlib import Path
from threading import Thread
from datetime import datetime

from fastapi import Request, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from lib.service import create_service
from lib.utils import joinpath, is_safe_path, generate_uuid

from pydantic import BaseModel



# Logging

logger = logging.getLogger(__name__)


# Service Instance
srv = create_service(__file__)

# Image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# Resize for pillow thumbnails
FORMAT_MAP = {
  ".jpg": "JPEG",
  ".jpeg": "JPEG",
  ".png": "PNG",
  ".gif": "GIF",
  ".webp": "WEBP",
  ".bmp": "BMP",
}

# Thumbnail Generation Queue
thumbnail_queue = Queue()
thumbnail_pending = set()

# File write model
class FileWriteRequest(BaseModel):
  filename: str
  content: str

# Create directory model
class DirectoryCreateRequest(BaseModel):
  dirname: str

# Copy / Move model
class CopyMoveRequest(BaseModel):
  source: str | list[str]
  dest: str

# Copy file model
class CopyFileRequest(BaseModel):
  source: str
  dest: str
  
  override: bool = False

# Rename model
class RenameRequest(BaseModel):
  source: str
  new_name: str

# Delete paths list model
class DeleteListModel(BaseModel):
  paths: list[str]

class FileCreateRequest(BaseModel):
  filename: str

# ========== Utils 
def to_list(value):
  return value if isinstance(value, list) else [value]

# ----------- Get unique path name if exists
def get_unique_path(path: str | Path) -> Path:
  path = Path(path)

  if not path.exists():
    return path

  counter = 1

  while True:
    if path.is_file():
      candidate = path.with_name(
        f"{path.stem} ({counter}){path.suffix}"
      )
    else:
      candidate = path.with_name(
        f"{path.name} ({counter})"
      )

    if not candidate.exists():
      return candidate

    counter += 1


# Only for apps
def resolve_app_path(app, path: str, read: bool) -> Path:
  core = srv.get_core()

  ptype = "read" if read else "write"
  storage = app.config.storage
  
  # splitting :// protocol
  if "://" in path:
    protocol, full_path = path.split("://", 1)
  else:
    # Fallback to data if no proto 
    protocol, full_path = "data", path

  # App data path (defalut) no permissions require
  if protocol == "data":
    return joinpath(app.get_app_data_path(), full_path)
  elif protocol == "app":
    if ptype == "write":
      srv.exception(400, "App path is read-only")

    return joinpath(app.get_app_path(), full_path)

  # Path maps
  path_maps = {
    "root": core.config.resolve_path("storage://"),
    "os": Path.home(),
    "osr": Path.cwd().anchor,

    "home": app.get_home_path()
  }

  if protocol in ["osr", "root"] and not app.is_sudo:
    srv.exception(404, "Sudo permission require to access root / osr")

  if protocol not in path_maps:
    srv.exception(404, "Invalid protocol")

  if not storage.check(protocol, ptype):
    srv.exception(400, f"Permission denied for {protocol}")

  return joinpath(path_maps[protocol], full_path)

# Only for clients
def resolve_client_path(client, path: str) -> Path:
  core = srv.get_core()
  return core.config.resolve_path(path)

# Resolve Path for client / app
def resolve_path(request: Request, path: str, read: bool = False) -> Path:
  client, app = srv.get_client_or_app(request)
  return resolve_app_path(app, path, read) if app else resolve_client_path(client, path)

# Generate thumbnail if dont exist
def generate_thumbnail(path: Path, size=(200, 200)) -> Path | None:
  if not path.exists() or not path.is_file():
    return None

  ext = path.suffix.lower()

  if ext not in IMAGE_EXTENSIONS:
    return None

  # Keep GIFs animated
  if ext == ".gif":
    return path
  
  # Already a thumbnail return it
  if path.parent.name == ".thumbnails":
    return path

  thumbnail_dir = path.parent / ".thumbnails"

  # create parents too, just in case :)
  thumbnail_dir.mkdir(parents=True, exist_ok=True)

  thumbnail_path = thumbnail_dir / path.name

  if thumbnail_path.exists():
    return thumbnail_path

  try:
    with Image.open(path) as img:
      img.thumbnail(size)

      if FORMAT_MAP[ext] == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

      img.save(thumbnail_path, FORMAT_MAP[ext])

    return thumbnail_path

  except Exception:
    return None

# Worker
def thumbnail_worker():
  while True:
    path = thumbnail_queue.get()

    try:
      generate_thumbnail(path)
    except Exception:
      pass
    finally:
      thumbnail_pending.discard(path)
      thumbnail_queue.task_done()

# Start worker thread
Thread(target=thumbnail_worker, daemon=True).start()

# Generate thumbnail if dont exist
def delete_thumbnail(path: Path) -> bool:
  if not path.exists() or not path.is_file():
    return False

  ext = path.suffix.lower()

  # GIFs don't have generated thumbnails
  if ext == ".gif":
    return False

  if ext not in IMAGE_EXTENSIONS:
    return False

  # Don't delete if this is already a thumbnail
  if path.parent.name == ".thumbnails":
    return False

  thumbnail_path = joinpath(path.parent / ".thumbnails", path.name)

  if thumbnail_path.exists():
    try:
      thumbnail_path.unlink()
      thumbnail_dir = thumbnail_path.parent

      # Remove the directory if it's empty
      try:
        thumbnail_dir.rmdir()
      except OSError:
        # Directory isn't empty or cant remove
        pass

      return True

    except Exception:
      return False
  return False

# Get path full info
def get_path_info(path: Path) -> dict:
  stat_result = path.stat()

  try:
    owner = path.owner()
  except (KeyError, OSError):
    owner = str(stat_result.st_uid)

  try:
    group = path.group()
  except (KeyError, OSError):
    group = str(stat_result.st_gid)
  
  is_dir = path.is_dir()

  items_count = None
  if is_dir:
    try:
      items_count = sum(1 for _ in path.iterdir())
    except (PermissionError, OSError):
      items_count = 0
  
  mime_type, encoding = mimetypes.guess_type(str(path))

  return {
    "name": path.name,
    "suffix": path.suffix,
    "directory": path.is_dir(),
    "items_count": items_count,
    "absolute_path": str(path.resolve()),
    "size_bytes": stat_result.st_size,
    "created": datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
    "modified": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
    "accessed": datetime.fromtimestamp(stat_result.st_atime).isoformat(),
    "owner": owner,
    "group": group,
    "permissions": oct(stat.S_IMODE(stat_result.st_mode)),
    "exists": path.exists(),
    "is_file": path.is_file(),
    "is_symlink": path.is_symlink(),
    "image_type": path.suffix.lower() in IMAGE_EXTENSIONS,

    "mime_type": mime_type,
    "encoding": encoding
  }

# ----------- Routes

class ExposeRouteModel(BaseModel):
  path: str

# ID: { app: appID, root: Path }
exposed_list = {}

def on_close_app(app_id: str):
  ex_list = [uid for uid, val in exposed_list.items() if val["type"] == "app" and val["id"] == app_id]
  
  for uid in ex_list:
    del exposed_list[uid]

    logger.info(f"App({app_id}) Exposed: {uid} removed.")

def on_close_client(client_id: str):
  ex_list = [uid for uid, val in exposed_list.items() if val["type"] == "client" and val["id"] == client_id]

  for uid in ex_list:
    del exposed_list[uid]
    
    logger.info(f"Client({client_id}) Exposed: {uid} removed.")


@srv.on("startup")
def startup(core):
  core.events.add_event("app:close", on_close_app)
  core.events.add_event("client:close", on_close_client)


# ----------- Expose

@srv.router.get("/thumbnail")
def thumbnail(request: Request, filename: str):
  path = Path(resolve_path(request, filename, True))
  
  thumbnail_path = joinpath(path.parent / ".thumbnails", path.name)

  if thumbnail_path.exists():
    return FileResponse(
      thumbnail_path,
      media_type="application/octet-stream"
    )

  return FileResponse(
    path,
    media_type="application/octet-stream"
  )

@srv.router.get("/list")
def list_files(
  request: Request,
  directory: str,       # Files directory
  offset: int = 0,      # start offset
  limit: int = -1,      # limit files
  sort: str = "name",   # name | size | modified
  asc: bool = True,     # files sorting order
  thumbnails=True       # Generate thumbnails
):
  dir_path = Path(resolve_path(request, directory, True))

  if not dir_path.exists() or not dir_path.is_dir():
    srv.exception(404, "Directory not found")

  offset = max(0, offset)
  limit = max(1, min(limit, 500)) if limit > 0 else None

  try:
    entries = list(dir_path.iterdir())

    if sort == "name":
      entries.sort(
        key=lambda p: (not p.is_dir(), p.name.lower()),
        reverse=not asc,
      )

    elif sort == "size":
      entries.sort(
        key=lambda p: (not p.is_dir(), p.stat().st_size),
        reverse=not asc,
      )

    elif sort == "modified":
      entries.sort(
        key=lambda p: (not p.is_dir(), p.stat().st_mtime),
        reverse=not asc,
      )

    else:
      srv.exception(400, "Invalid sort field")

    total = len(entries)

    files = []
    
    for path in entries[offset:offset + limit] if limit else entries:
      try:
        files.append(get_path_info(path))
        # If its image then generate thumbnail
        if (
          thumbnail
          and path.is_file()
          and path.suffix.lower() in IMAGE_EXTENSIONS
        ):
          thumb = joinpath(path.parent / ".thumbnails", path.name)

          if (
            not thumb.exists()
            and path not in thumbnail_pending
          ):
            thumbnail_pending.add(path)
            thumbnail_queue.put(path)
      except (PermissionError, OSError, FileNotFoundError, Exception):
        continue

    return {
      "directory": directory,
      "offset": offset,
      "limit": limit,
      "count": len(files),
      "total": total,
      "has_more": offset + len(files) < total if limit else False,
      "sort": sort,
      "asc": asc,
      "files": files,
    }

  except PermissionError:
    srv.exception(403, "OS permission error")
  except Exception as e:
    srv.exception(500, str(e))

@srv.router.get("/read")
def read_file(request: Request, filename: str) -> StreamingResponse:
  file_path = resolve_path(request, filename, True)

  if not os.path.exists(file_path):
    srv.exception(404, "File not found")

  def file_generator():
    with open(file_path, "rb") as file:
      while chunk := file.read(1024 * 1024):
        yield chunk

  return StreamingResponse(file_generator(), media_type="application/octet-stream")

@srv.router.post("/write")
def write_file(request: Request, file: FileWriteRequest) -> dict:
  file_path = resolve_path(request, file.filename)
  
  if file_path.is_dir():
    srv.exception(401, "Folder exists with same name")

  try:
    with open(file_path, "w", encoding="utf-8") as f:
      f.write(file.content)
  except FileNotFoundError:
    srv.exception(404, "File not found")
  except (PermissionError, OSError):
    srv.exception(403, "Permission denied")
  except Exception:
    srv.exception(500, "Error creating file")

  logger.info(f"Wrote to file {file_path}")
  return {"message": "File written successfully", "filename": file.filename}

@srv.router.delete("/delete")
def delete_file(request: Request, filename: str) -> dict:
  file_path = resolve_path(request, filename)

  if not os.path.exists(file_path):
    srv.exception(404, "File not found")

  delete_thumbnail(file_path)
  os.remove(file_path)

  logger.info(f"Deleted file {file_path}")
  return {"message": "File deleted successfully"}

@srv.router.post("/upload")
async def upload_files(request: Request, dest: str, files: list[UploadFile] = File(...)):
  uploaded = []

  for file in files:
    original_path = joinpath(resolve_path(request, dest), file.filename)

    file_path = get_unique_path(original_path)

    with open(file_path, "wb") as f:
      while chunk := await file.read(1024 * 1024):
        f.write(chunk)

    uploaded.append(Path(file_path).name)
    logger.info(f"Uploaded file to {file_path}")

  return {
    "message": "Files uploaded successfully",
    "count": len(uploaded),
    "filenames": uploaded,
  }

@srv.router.post("/create_file")
def create_file(request: Request, file_request: FileCreateRequest) -> dict:
  file_path = resolve_path(request, file_request.filename)

  if os.path.exists(file_path):
    srv.exception(403, "File already exists")

  # Create parent directories if they don't exist (optional)
  os.makedirs(os.path.dirname(file_path), exist_ok=True)

  # Create an empty file
  with open(file_path, "x"):
    pass

  logger.info(f"Created file {file_path}")
  return {"message": "File created successfully"}

@srv.router.post("/create_directory")
def create_directory(request: Request, dir_request: DirectoryCreateRequest) -> dict:
  dir_path = resolve_path(request, dir_request.dirname)

  if os.path.exists(dir_path):
    srv.exception(403, "Directory already exists")

  os.makedirs(dir_path)
  logger.info(f"Created directory {dir_path}")
  return { "message": "Directory created successfully" }

@srv.router.post("/rename")
def rename_item(request: Request, payload: RenameRequest) -> dict:
  src_path = resolve_path(request, payload.source)
  delete_thumbnail(src_path)

  if not src_path.exists():
    srv.exception(404, "File not found")

  dest_path = joinpath(src_path.parent, payload.new_name)

  if dest_path.exists():
    srv.exception(409, "Destination already exists")

  try:
    src_path.rename(dest_path)
  except (PermissionError, OSError):
    srv.exception(403, "Permission Denied")
  except Exception:
    srv.exception(500, "Error renaming")

  logger.info(f"Renamed {src_path} -> {dest_path}")

  return {
    "message": "Rename successful",
    "old_name": src_path.name,
    "new_name": payload.new_name
  }

# ----------- Delete dir / Paths list

@srv.router.post("/delete-list")
def delete_list_paths(request: Request, payload: DeleteListModel) -> dict:
  deleted_list = []
  
  for path in payload.paths:
    fpath = resolve_path(request, path)
    delete_thumbnail(fpath)

    if not fpath.exists():
      continue
    
    if fpath.is_file():
      os.remove(fpath)
    else:
      shutil.rmtree(fpath)

    deleted_list.append(path)

    logger.info(f"Deleted path {fpath}")

  return { "message": "Paths deleted successfully", "deleted": deleted_list }

@srv.router.delete("/delete_directory")
def delete_directory(request: Request, dirname: str) -> dict:
  dir_path = resolve_path(request, dirname)

  if not os.path.exists(dir_path):
    srv.exception(404, "Directory not found")

  shutil.rmtree(dir_path)
  logger.info(f"Deleted directory {dir_path}")
  return {"message": "Directory deleted successfully"}

# ----------- Copy / Move

@srv.router.post("/copy-file")
def copy_file(request: Request, payload: CopyFileRequest) -> dict:
  try:
    src_path = resolve_path(request, payload.source, True)
    dest_path = resolve_path(request, payload.dest)

    if not src_path.is_file():
      srv.exception(404, "Source file not found")

    # If destination is a directory, keep the source filename
    if dest_path.is_dir():
      dest_path = dest_path / src_path.name

    if not payload.override:
      dest_path = get_unique_path(dest_path)

    # Ensure parent directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src_path, dest_path)

    logger.info(f"Copied file from {src_path} to {dest_path}")

    return {
      "message": "File copied successfully",
      "source": payload.source,
      "destination": str(dest_path),
      "filename": dest_path.name,
    }
  except Exception as e:
    srv.exception(500, e)

@srv.router.post("/copy")
def copy_item(request: Request, payload: CopyMoveRequest) -> dict:
  sources = to_list(payload.source)
  dest_dir = resolve_path(request, payload.dest)

  copied = []
  
  try:
    os.makedirs(dest_dir, exist_ok=True)
    
    for source in sources:
      try:
        src_path = resolve_path(request, source, True)

        if not os.path.exists(src_path):
          continue

        target = get_unique_path(
          Path(dest_dir) / os.path.basename(src_path)
        )

        if os.path.isdir(src_path):
          shutil.copytree(src_path, target)
        else:
          shutil.copy2(src_path, target)

        copied.append(source)
        logger.info(f"Copied from {src_path} to {target}")
      except Exception as e:
        logger.exception(f"Failed to process {source}: {e}")
        continue
  except Exception as e:
    srv.exception(500, e)

  return {
    "message": "Copy successful",
    "count": len(copied),
    "destination": payload.dest,
    "sources": copied
  }

@srv.router.post("/move")
def move_item(request: Request, payload: CopyMoveRequest) -> dict:
  sources = to_list(payload.source)
  dest_dir = resolve_path(request, payload.dest)

  moved = []
  
  try:
    for source in sources:
      try:
        src_path = resolve_path(request, source, True)
        delete_thumbnail(src_path)
  
        if not os.path.exists(src_path):
          continue
  
        target = get_unique_path(
          Path(dest_dir) / os.path.basename(src_path)
        )
        
        os.makedirs(dest_dir, exist_ok=True)

        shutil.move(src_path, str(target))
  
        moved.append(source)
        logger.info(f"Moved from {src_path} to {target}")
      except Exception as e:
        logger.exception(f"Failed to process {source}: {e}")
        continue
  except Exception as e:
    srv.exception(500, e)

  return {
    "message": "Move successful",
    "count": len(moved),
    "destination": payload.dest,
    "sources": moved
  }

# ----------- Info

@srv.router.get("/info")
def path_info(request: Request, path: str):
  file_path = resolve_path(request, path, True)
  
  print(path, file_path)

  if not file_path.exists():
    srv.exception(404, "File not found")

  try:
    return get_path_info(file_path)
  except Exception as e:
    srv.exception(500, e)

@srv.router.post("/expose")
async def expose_path(request: Request, payload: ExposeRouteModel):
  path = resolve_path(request, payload.path, True)
  if not path.exists():
    srv.exception(404, "Path not found")

  client, app = srv.get_client_or_app(request)

  uid = generate_uuid()
  
  exposed_list[uid] = {
    "id": app.id if app else client.id,
    "root": path,
    "type": "app" if app else "client"
  }
  
  return uid

@srv.router.delete("/expose")
async def del_expose_path(request: Request, uid: str):
  if uid not in exposed_list:
    srv.exception(404, "uid not found")
  
  del exposed_list[uid]
  
  return srv.ok()

@srv.router.get("/clear-expose")
async def clear_expose(request: Request):
  client, app = srv.get_client_or_app(request)

  on_close_app(app.id) if app else on_close_client(client.id)

  return srv.ok()

@srv.router.get("/serve/{uid}/{path:path}")
async def serve(uid: str, path: str | None = None):
  ex = exposed_list.get(uid)
  if ex is None:
    srv.exception(404, "uid not found")

  fpath = joinpath(ex["root"], path) if len(path) > 0 else ex["root"]

  if not fpath.exists():
    srv.exception(404, "Invalid Path")
  
  return FileResponse(fpath)
