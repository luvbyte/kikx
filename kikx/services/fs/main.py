import os
import shutil
import logging

from queue import Queue
from pathlib import Path
from threading import Thread, Lock

from fastapi import Request, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from lib.utils import joinpath
from lib.service import create_service

from .expose import ExposedPaths
from .models import (
  FileWriteRequest,
  DirectoryCreateRequest,
  CopyMoveRequest,
  CopyFileRequest,
  RenameRequest,
  DeleteListModel,
  FileCreateRequest,
  ExposeRouteModel
)
from .utils import (
  to_list,
  get_path_info,
  get_unique_path,
  generate_thumbnail,
  delete_thumbnail,
  IMAGE_EXTENSIONS,
)


# Logging

logger = logging.getLogger(__name__)


# Service Instance

srv = create_service(__file__)
expose = ExposedPaths(srv)


# Worker

thumbnail_queue = Queue()
thumbnail_pending = set()
thumbnail_lock = Lock()


def queue_thumbnail(path: Path):
  thumb = path.parent / ".thumbnails" / path.name

  if thumb.exists():
    return

  with thumbnail_lock:
    if path in thumbnail_pending:
      return

    thumbnail_pending.add(path)
    thumbnail_queue.put(path)


def thumbnail_worker():
  while True:
    path = thumbnail_queue.get()

    try:
      generate_thumbnail(path)
    except FileNotFoundError:
      pass
    except Exception:
      logger.exception("Thumbnail generation failed: %s", path.name)
    finally:
      with thumbnail_lock:
        thumbnail_pending.discard(path)
      thumbnail_queue.task_done()


Thread(target=thumbnail_worker, daemon=True).start()


# Helpers

def ensure_filename(filename: str):
  if not filename or filename in {".", ".."}:
    srv.exception(400, "Invalid filename")

  # Rename/upload should only receive a filename, not another path.
  if Path(filename).name != filename:
    srv.exception(400, "Invalid filename")


def ensure_not_inside(source: Path, destination: Path):
  if not source.is_dir():
    return

  try:
    destination.resolve(strict=False).relative_to(
      source.resolve(strict=False)
    )
  except ValueError:
    return

  srv.exception(400, "Cannot copy or move a directory into itself")


def safe_delete_thumbnail(path: Path):
  try:
    delete_thumbnail(path)
  except Exception:
    logger.warning("Failed to delete thumbnail: %s", path.name)


# Resolve

def check_storage(fs_config, storage, permission_type) -> bool:
  if fs_config is None:
    return False

  permission = getattr(fs_config, storage, None)

  if permission is None or permission == "none":
    return False

  return permission in {permission_type, "read-write"}


def resolve_app_path(app, path: str, read: bool) -> Path:
  core = srv.get_core()

  if not app.config.has_service("fs"):
    srv.exception(403, "Service 'fs' not found in config")

  # Split protocol://path.
  if "://" in path:
    protocol, full_path = path.split("://", 1)
  else:
    protocol, full_path = "data", path

  # App data path.
  if protocol == "data":
    return joinpath(app.get_app_data_path(), full_path)

  # App cache path.
  if protocol == "cache":
    return joinpath(app.get_app_cache_path(), full_path)

  # App installation path is read-only.
  if protocol == "app":
    if not read:
      srv.exception(400, "App path is read-only")

    return joinpath(app.get_app_path(), full_path)

  path_maps = {
    "root": core.config.resolve_path("storage://"),
    "os": Path.home(),
    "osr": Path.cwd().anchor,
    "home": app.get_home_path(),
  }

  # Root and OS root require sudo.
  if protocol in {"osr", "root"} and not app.is_sudo:
    srv.exception(404, "Sudo permission require to access root / osr")

  if protocol not in path_maps:
    srv.exception(404, "Invalid protocol")

  permission = "read" if read else "write"

  if not check_storage(
    app.config.get_service_config("fs"),
    protocol,
    permission,
  ):
    srv.exception(400, f"Permission denied for {protocol}")

  return joinpath(path_maps[protocol], full_path)


def resolve_client_path(client, path: str) -> Path:
  core = srv.get_core()
  return core.config.resolve_path(path)


def resolve_path(request: Request, path: str, read: bool = False) -> Path:
  client, app = srv.get_client_or_app(request)
  return resolve_app_path(app, path, read) if app else resolve_client_path(client, path)


# Lifecycle

@srv.on("startup")
def startup(core):
  core.events.add_event("app:close", expose.clear_app)
  core.events.add_event("client:close", expose.clear_client)


# Thumbnail

@srv.router.get("/thumbnail")
def thumbnail(request: Request, filename: str):
  path = Path(resolve_path(request, filename, True))

  thumbnail_path = path.parent / ".thumbnails" / path.name
  file_path = thumbnail_path if thumbnail_path.is_file() else path

  if not file_path.is_file():
    srv.exception(404, "File not found")

  return FileResponse(
    file_path,
    media_type="application/octet-stream",
  )


# List

@srv.router.get("/list")
def list_files(
  request: Request,
  directory: str,
  offset: int = 0,
  limit: int = -1,
  sort: str = "name",
  asc: bool = True,
  thumbnails: bool = True,
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
    selected = entries[offset:] if limit is None else entries[offset:offset + limit]

    files = []

    for path in selected:
      try:
        files.append(get_path_info(path))

        if (
          thumbnails
          and path.is_file()
          and path.suffix.lower() in IMAGE_EXTENSIONS
        ):
          queue_thumbnail(path)

      except (PermissionError, OSError, FileNotFoundError):
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
  except OSError:
    logger.exception("Failed to list directory: %s", directory)
    srv.exception(500, "Failed to list directory")


# Read

@srv.router.get("/read")
def read_file(request: Request, filename: str) -> StreamingResponse:
  file_path = resolve_path(request, filename, True)

  if not file_path.is_file():
    srv.exception(404, "File not found")

  def file_generator():
    try:
      with open(file_path, "rb") as file:
        while chunk := file.read(1024 * 1024):
          yield chunk
    except OSError:
      logger.exception("Failed to read file: %s", filename)

  return StreamingResponse(file_generator(), media_type="application/octet-stream")


# Write

@srv.router.post("/write")
def write_file(request: Request, file: FileWriteRequest) -> dict:
  file_path = resolve_path(request, file.filename)

  if file_path.is_dir():
    srv.exception(409, "Invalid file path")

  mode_mapping = {
    "write": "w",
    "append": "a",
  }

  if file.mode not in mode_mapping:
    srv.exception(400, "Invalid file mode")

  if file.ensure_dir:
    try:
      file_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
      srv.exception(403, "Permission denied")
    except OSError:
      logger.exception("Failed to create parent directory: %s", file.filename)
      srv.exception(500, "Error creating directory")

  try:
    with open(file_path, mode_mapping[file.mode], encoding="utf-8") as f:
      f.write(file.content)
  except FileNotFoundError:
    srv.exception(404, "File not found")
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to write file: %s", file.filename)
    srv.exception(500, "Error writing file")

  logger.info("File written: %s", file.filename)

  return {
    "message": "File written successfully",
    "filename": file.filename,
    "mode": file.mode,
  }


# Delete File

@srv.router.delete("/delete")
def delete_file(request: Request, filename: str) -> dict:
  file_path = resolve_path(request, filename)

  if not file_path.exists() and not file_path.is_symlink():
    srv.exception(404, "File not found")

  if not file_path.is_file() and not file_path.is_symlink():
    srv.exception(409, "Path is not a file")

  safe_delete_thumbnail(file_path)

  try:
    file_path.unlink()
  except FileNotFoundError:
    srv.exception(404, "File not found")
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to delete file: %s", filename)
    srv.exception(500, "Error deleting file")

  logger.info("File deleted: %s", filename)

  return {
    "message": "File deleted successfully",
  }


# Upload

@srv.router.post("/upload")
async def upload_files(
  request: Request,
  dest: str,
  files: list[UploadFile] = File(...),
):
  uploaded = []
  failed = []

  dest_path = resolve_path(request, dest)

  try:
    dest_path.mkdir(parents=True, exist_ok=True)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to create upload directory: %s", dest)
    srv.exception(500, "Failed to create upload destination")

  for file in files:
    filename = file.filename or "unnamed"

    try:
      ensure_filename(filename)

      file_path = get_unique_path(
        joinpath(dest_path, filename)
      )

      with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
          f.write(chunk)

      uploaded.append(Path(file_path).name)
      logger.info("File uploaded: %s", Path(file_path).name)

    except Exception:
      failed.append(filename)
      logger.exception("Failed to upload file: %s", filename)

    finally:
      await file.close()

  return {
    "message": "Files uploaded successfully" if not failed else "Upload completed with errors",
    "count": len(uploaded),
    "filenames": uploaded,
    "failed": failed,
  }


# Download

@srv.router.get("/download")
def download_file(request: Request, path: str):
  fpath = resolve_path(request, path, True)

  if not fpath.is_file():
    srv.exception(404, "File not found")

  return FileResponse(
    fpath,
    filename=fpath.name,
    media_type="application/octet-stream",
  )


# Create File

@srv.router.post("/create_file")
def create_file(request: Request, file_request: FileCreateRequest) -> dict:
  file_path = resolve_path(request, file_request.filename)

  try:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # "x" creates only when the file does not already exist.
    with open(file_path, "x"):
      pass

  except FileExistsError:
    srv.exception(409, "File already exists")
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to create file: %s", file_request.filename)
    srv.exception(500, "Error creating file")

  logger.info("File created: %s", file_request.filename)

  return {
    "message": "File created successfully",
  }


# Create Directory

@srv.router.post("/create_directory")
def create_directory(
  request: Request,
  dir_request: DirectoryCreateRequest,
) -> dict:
  dir_path = resolve_path(request, dir_request.dirname)

  try:
    dir_path.mkdir(parents=True, exist_ok=False)
  except FileExistsError:
    srv.exception(409, "Directory already exists")
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to create directory: %s", dir_request.dirname)
    srv.exception(500, "Error creating directory")

  logger.info("Directory created: %s", dir_request.dirname)

  return {
    "message": "Directory created successfully",
  }


# Rename

@srv.router.post("/rename")
def rename_item(request: Request, payload: RenameRequest) -> dict:
  src_path = resolve_path(request, payload.source)

  if not src_path.exists():
    srv.exception(404, "File not found")

  ensure_filename(payload.new_name)

  dest_path = joinpath(src_path.parent, payload.new_name)

  if dest_path.exists():
    srv.exception(409, "Destination already exists")

  try:
    src_path.rename(dest_path)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception(
      "Failed to rename %s to %s",
      payload.source,
      payload.new_name,
    )
    srv.exception(500, "Error renaming")

  # Delete only after the rename succeeded.
  safe_delete_thumbnail(src_path)

  logger.info(
    "Item renamed: %s -> %s",
    payload.source,
    payload.new_name,
  )

  return {
    "message": "Rename successful",
    "old_name": src_path.name,
    "new_name": payload.new_name,
  }


# Delete List

@srv.router.post("/delete-list")
def delete_list_paths(
  request: Request,
  payload: DeleteListModel,
) -> dict:
  deleted_list = []
  failed = []

  for path in payload.paths:
    try:
      fpath = resolve_path(request, path)

      if not fpath.exists() and not fpath.is_symlink():
        continue

      safe_delete_thumbnail(fpath)

      if fpath.is_file() or fpath.is_symlink():
        fpath.unlink()
      elif fpath.is_dir():
        shutil.rmtree(fpath)
      else:
        failed.append(path)
        continue

      deleted_list.append(path)

    except PermissionError:
      failed.append(path)
      logger.warning("Permission denied deleting: %s", path)

    except OSError:
      failed.append(path)
      logger.exception("Failed to delete: %s", path)

  return {
    "message": "Paths deleted successfully" if not failed else "Delete completed with errors",
    "deleted": deleted_list,
    "failed": failed,
  }


# Delete Directory

@srv.router.delete("/delete_directory")
def delete_directory(request: Request, dirname: str) -> dict:
  dir_path = resolve_path(request, dirname)

  if not dir_path.exists():
    srv.exception(404, "Directory not found")

  if not dir_path.is_dir():
    srv.exception(409, "Path is not a directory")

  try:
    shutil.rmtree(dir_path)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to delete directory: %s", dirname)
    srv.exception(500, "Error deleting directory")

  logger.info("Directory deleted: %s", dirname)

  return {
    "message": "Directory deleted successfully",
  }


# Copy File

@srv.router.post("/copy-file")
def copy_file(request: Request, payload: CopyFileRequest) -> dict:
  src_path = resolve_path(request, payload.source, True)

  if not src_path.is_file():
    srv.exception(404, "Source file not found")

  dest_path = resolve_path(request, payload.dest)

  # If destination is a directory, keep the source filename.
  if dest_path.is_dir():
    dest_path = dest_path / src_path.name

  if not payload.override:
    dest_path = get_unique_path(dest_path)

  try:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception(
      "Failed to copy %s to %s",
      payload.source,
      payload.dest,
    )
    srv.exception(500, "File copy failed")

  logger.info(
    "File copied: %s -> %s",
    payload.source,
    payload.dest,
  )

  return {
    "message": "File copied successfully",
    "source": payload.source,
    "destination": str(dest_path),
    "filename": dest_path.name,
  }


# Copy

@srv.router.post("/copy")
def copy_item(request: Request, payload: CopyMoveRequest) -> dict:
  sources = to_list(payload.source)
  dest_dir = resolve_path(request, payload.dest)

  copied = []
  failed = []

  try:
    dest_dir.mkdir(parents=True, exist_ok=True)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to create copy destination: %s", payload.dest)
    srv.exception(500, "Copy failed")

  for source in sources:
    try:
      src_path = resolve_path(request, source, True)

      if not src_path.exists():
        failed.append(source)
        continue

      target = get_unique_path(dest_dir / src_path.name)

      ensure_not_inside(src_path, target)

      if src_path.is_dir():
        shutil.copytree(src_path, target)
      elif src_path.is_file():
        shutil.copy2(src_path, target)
      else:
        failed.append(source)
        continue

      copied.append(source)

    except PermissionError:
      failed.append(source)
      logger.warning("Permission denied copying: %s", source)

    except OSError:
      failed.append(source)
      logger.exception("Failed to copy: %s", source)

    except Exception:
      failed.append(source)
      logger.exception("Unexpected copy error: %s", source)

  logger.info(
    "Copy completed | copied=%d | failed=%d",
    len(copied),
    len(failed),
  )

  return {
    "message": "Copy successful" if not failed else "Copy completed with errors",
    "count": len(copied),
    "destination": payload.dest,
    "sources": copied,
    "failed": failed,
  }


# Move

@srv.router.post("/move")
def move_item(request: Request, payload: CopyMoveRequest) -> dict:
  sources = to_list(payload.source)
  dest_dir = resolve_path(request, payload.dest)

  moved = []
  failed = []

  try:
    dest_dir.mkdir(parents=True, exist_ok=True)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to create move destination: %s", payload.dest)
    srv.exception(500, "Move failed")

  for source in sources:
    try:
      src_path = resolve_path(request, source, True)

      if not src_path.exists():
        failed.append(source)
        continue

      target = get_unique_path(dest_dir / src_path.name)

      ensure_not_inside(src_path, target)

      shutil.move(str(src_path), str(target))

      # Remove the old thumbnail only after a successful move.
      safe_delete_thumbnail(src_path)

      moved.append(source)

    except PermissionError:
      failed.append(source)
      logger.warning("Permission denied moving: %s", source)

    except OSError:
      failed.append(source)
      logger.exception("Failed to move: %s", source)

    except Exception:
      failed.append(source)
      logger.exception("Unexpected move error: %s", source)

  logger.info(
    "Move completed | moved=%d | failed=%d",
    len(moved),
    len(failed),
  )

  return {
    "message": "Move successful" if not failed else "Move completed with errors",
    "count": len(moved),
    "destination": payload.dest,
    "sources": moved,
    "failed": failed,
  }


# Info

@srv.router.get("/info")
def path_info(request: Request, path: str):
  file_path = resolve_path(request, path, True)

  if not file_path.exists():
    srv.exception(404, "File not found")

  try:
    return get_path_info(file_path)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to get path info: %s", path)
    srv.exception(500, "Failed to get path information")


# Expose

@srv.router.post("/expose")
def expose_path(request: Request, payload: ExposeRouteModel):
  path = resolve_path(request, payload.path, True)

  if not path.exists():
    srv.exception(404, "Path not found")

  client, app = srv.get_client_or_app(request)

  uid = expose.add(
    path,
    app.id if app else client.id,
    "app" if app else "client",
    expires=payload.expires,
  )

  logger.info("Path exposed: %s", payload.path)

  return {
    "uid": uid,
  }


@srv.router.delete("/expose")
def del_expose_path(request: Request, uid: str):
  client, app = srv.get_client_or_app(request)

  if app:
    expose.remove_app(uid, app.id)
  else:
    expose.remove_client(uid, client.id)

  logger.info("Exposed path removed: %s", uid)

  return srv.ok("Successfully removed")


@srv.router.get("/clear-expose")
def clear_expose(request: Request):
  client, app = srv.get_client_or_app(request)

  if app:
    length = expose.clear_app(app.id)
  else:
    length = expose.clear_client(client.id)

  logger.info("Exposed paths cleared: %d", length)

  return srv.ok(f"Successfully removed {length} paths")


# Serve Exposed File

@srv.router.get("/serve/{uid}/{path:path}")
def serve(uid: str, path: str | None = None):
  expose.check_uid(uid)

  fpath = expose.get_path(uid, path)

  if fpath is None or not fpath.is_file():
    srv.exception(404, "File not found")

  return FileResponse(
    fpath,
    filename=fpath.name,
    content_disposition_type="attachment",
  )