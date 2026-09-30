import os
import json
import uuid
import time
import shutil
import zipfile
import hashlib
import tarfile
import mimetypes
import logging

from queue import Queue
from pathlib import Path
from threading import Thread, Lock

from datetime import datetime, timezone
from fastapi import Request, UploadFile, File, Body
from fastapi.responses import FileResponse, StreamingResponse

from lib.utils import joinpath
from lib.service import create_service

from .expose import ExposedPaths
from .config import IMAGE_EXTENSIONS 

from .models import (
  FileWriteRequest,
  DirectoryCreateRequest,
  CopyMoveRequest,
  CopyFileRequest,
  RenameRequest,
  DeleteListModel,
  FileCreateRequest,
  ExposeRouteModel,
  BatchOperation
)
from .utils import (
  to_list,
  get_path_info,
  get_unique_path,
  generate_thumbnail,
  delete_thumbnail
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


def _file_timestamp(timestamp):
  return datetime.fromtimestamp(
    timestamp,
    timezone.utc
  ).isoformat()


def _safe_archive_member(base, member):
  base = Path(base).resolve()

  target = (base / member).resolve()

  try:
    target.relative_to(base)
  except ValueError:
    return False

  return True


def _directory_snapshot(path):
  snapshot = {}

  root_path = str(
    Path(path).resolve()
  )

  stack = [root_path]

  while stack:
    current = stack.pop()

    try:
      with os.scandir(current) as entries:
        for entry in entries:
          try:
            stat = entry.stat(
              follow_symlinks=False
            )

            is_dir = entry.is_dir(
              follow_symlinks=False
            )

            relative_path = os.path.relpath(
              entry.path,
              root_path
            )

            snapshot[relative_path] = (
              stat.st_mtime_ns,
              stat.st_size,
              is_dir
            )

            if is_dir:
              stack.append(entry.path)

          except OSError:
            continue

    except OSError:
      continue

  return snapshot


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


def convert_path(request, path, path_type="virtual"):
  if not isinstance(path, str):
    srv.exception(400, "Path must be a string")

  path = path.strip()

  if not path:
    srv.exception(400, "Path cannot be empty")

  if path_type not in {"virtual", "absolute"}:
    srv.exception(400, "Invalid path_type")

  # Absolute OS path -> KIKX virtual path
  if path_type == "virtual":
    absolute_path = Path(path).resolve()

    protocols = [
      "data://",
      "cache://",
      "app://",
      "root://",
      "os://",
      "osr://",
      "home://"
    ]

    for protocol in protocols:
      try:
        root_path = resolve_path(
          request,
          protocol,
          True
        ).resolve()

        try:
          relative = absolute_path.relative_to(
            root_path
          )
        except ValueError:
          continue

        if str(relative) == ".":
          return protocol

        return (
          f"{protocol}"
          f"{relative.as_posix()}"
        )

      except Exception:
        continue

    srv.exception(
      400,
      "Path is outside KIKX virtual paths"
    )

  # KIKX virtual path -> absolute OS path
  absolute_path = resolve_path(
    request,
    path,
    True
  )

  return str(Path(absolute_path).resolve())


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

@srv.router.get("/list-simple")
def simple_list(
  request: Request,
  directory: str,
  sort: str = "name",
  asc: bool = True,
  filter: str = "all",
  extensions: str = "",
  search: str = "",
  hidden: bool = True,
):
  dir_path = resolve_path(request, directory, True)

  sort = sort.lower()
  filter = filter.lower()
  search = search.lower().strip()

  if sort not in {"name", "size", "modified"}:
    srv.exception(400, "Invalid sort field")

  if filter not in {"all", "files", "directories", "images"}:
    srv.exception(400, "Invalid filter")

  extension_set = set()

  if extensions:
    for ext in extensions.split(","):
      ext = ext.strip().lower()
      if ext:
        extension_set.add(ext if ext.startswith(".") else f".{ext}")

  try:
    entries = []

    with os.scandir(dir_path) as scanner:
      for entry in scanner:
        name = entry.name

        if not hidden and name.startswith("."):
          continue

        if search and search not in name.lower():
          continue

        try:
          is_file = entry.is_file(follow_symlinks=False)
          is_dir = entry.is_dir(follow_symlinks=False)
        except OSError:
          continue

        suffix = os.path.splitext(name)[1].lower()

        if filter == "files" and not is_file:
          continue

        if filter == "directories" and not is_dir:
          continue

        if filter == "images" and (not is_file or suffix not in IMAGE_EXTENSIONS):
          continue

        if extension_set and (not is_file or suffix not in extension_set):
          continue

        size = None
        modified = None

        if sort in {"size", "modified"}:
          try:
            stat_result = entry.stat(follow_symlinks=False)
            size = stat_result.st_size
            modified = stat_result.st_mtime
          except OSError:
            continue
        
        relative_path = os.path.relpath(entry.path, dir_path)
        if directory.endswith("://"):
          kikxpath = f"{directory}{relative_path}"
        else: 
          kikxpath = f"{directory.rstrip('/')}/{relative_path.lstrip('/')}"

        entries.append((name, entry.path, is_file, is_dir, suffix, size, modified, kikxpath))

  except FileNotFoundError:
    srv.exception(404, "Directory not found")
  except NotADirectoryError:
    srv.exception(404, "Directory not found")
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to list directory: %s", directory)
    srv.exception(500, "Failed to list directory")

  if sort == "name":
    entries.sort(key=lambda x: (not x[3], x[0].lower()), reverse=not asc)
  elif sort == "size":
    entries.sort(key=lambda x: (not x[3], x[5] or 0), reverse=not asc)
  elif sort == "modified":
    entries.sort(key=lambda x: (not x[3], x[6] or 0), reverse=not asc)

  files = [
    {
      "name": name,
      "path": path,
      "kikxpath": kikxpath,
      "directory": is_dir,
      "is_file": is_file,
      "suffix": suffix,
      # only works if sort is size
      "size": size,
      "modified": modified
    }
    for name, path, is_file, is_dir, suffix, size, modified, kikxpath in entries
  ]

  return {
    "directory": directory,
    "count": len(files),
    "files": files,
  }

@srv.router.get("/list")
def list_files(
  request: Request,
  directory: str,
  offset: int = 0,
  limit: int = -1,
  sort: str = "name",
  asc: bool = True,
  filter: str = "all",
  extensions: str = "",
  search: str = "",
  thumbnails: bool = False,
):
  dir_path = Path(resolve_path(request, directory, True))

  offset = max(0, offset)
  limit = max(1, min(limit, 500)) if limit > 0 else None

  filter = filter.lower()
  search = search.lower().strip()
  extension_set = set()

  if filter not in {"all", "files", "directories", "images"}:
    srv.exception(400, "Invalid filter")

  if extensions:
    for ext in extensions.split(","):
      ext = ext.strip().lower()
      if ext:
        extension_set.add(ext if ext.startswith(".") else f".{ext}")

  try:
    with os.scandir(dir_path) as scanner:
      entries = []

      for entry in scanner:
        try:
          name = entry.name
          suffix = Path(name).suffix.lower()
          is_file = entry.is_file(follow_symlinks=False)
          is_dir = entry.is_dir(follow_symlinks=False)

          if search and search not in name.lower():
            continue

          if filter == "files" and not is_file:
            continue

          if filter == "directories" and not is_dir:
            continue

          if filter == "images" and (not is_file or suffix not in IMAGE_EXTENSIONS):
            continue

          if extension_set and (not is_file or suffix not in extension_set):
            continue

          entries.append(entry)

        except OSError:
          continue

    if sort == "name":
      entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()), reverse=not asc)
    elif sort == "size":
      entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.stat(follow_symlinks=False).st_size), reverse=not asc)
    elif sort == "modified":
      entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.stat(follow_symlinks=False).st_mtime), reverse=not asc)
    else:
      srv.exception(400, "Invalid sort field")

    total = len(entries)
    selected = entries[offset:] if limit is None else entries[offset:offset + limit]

    files = []

    for entry in selected:
      try:
        path = Path(entry.path)

        relative_path = os.path.relpath(entry.path, dir_path)
        if directory.endswith("://"):
          kikxpath = f"{directory}{relative_path}"
        else: 
          kikxpath = f"{directory.rstrip('/')}/{relative_path.lstrip('/')}"

        files.append(get_path_info(path, kikxpath))
        
        if thumbnails and entry.is_file(follow_symlinks=False) and path.suffix.lower() in IMAGE_EXTENSIONS:
          queue_thumbnail(path)

      except OSError:
        continue

    count = len(files)

    return {
      "directory": directory,
      "offset": offset,
      "limit": limit,
      "count": count,
      "total": total,
      "has_more": offset + count < total if limit else False,
      "sort": sort,
      "asc": asc,
      "filter": filter,
      "extension": extensions,
      "search": search,
      "files": files,
    }

  except FileNotFoundError:
    srv.exception(404, "Directory not found")
  except NotADirectoryError:
    srv.exception(404, "Directory not found")
  except PermissionError:
    srv.exception(403, "OS permission error")
  except OSError:
    logger.exception("Failed to list directory: %s", directory)
    srv.exception(500, "Failed to list directory")

# Search

@srv.router.get("/search")
def search_files(
  request: Request,
  directory: str,
  search: str = "",
  filter: str = "all",
  extensions: str = "",
  hidden: bool = True,
  max_results: int = -1,
):
  dir_path = resolve_path(request, directory, True)

  search = search.strip().lower()
  filter = filter.lower()

  if filter not in {"all", "files", "directories", "images"}:
    srv.exception(400, "Invalid filter")

  if max_results == 0 or max_results < -1:
    srv.exception(400, "Invalid max_results")

  # Limit bounded searches.
  if max_results > 5000:
    max_results = 5000

  # Normalize extensions.
  extension_set = set()

  if extensions:
    extension_set = {
      ext.strip().lower()
      if ext.strip().startswith(".")
      else f".{ext.strip().lower()}"
      for ext in extensions.split(",")
      if ext.strip()
    }

  if not dir_path.is_dir():
    srv.exception(404, "Directory not found")

  results = []

  # Directories waiting to be scanned.
  stack = [str(dir_path)]

  root_path = str(dir_path)

  while stack and (
    max_results == -1 or len(results) < max_results
  ):
    current = stack.pop()

    try:
      with os.scandir(current) as entries:
        for entry in entries:

          if (
            max_results != -1
            and len(results) >= max_results
          ):
            break

          name = entry.name

          # Skip hidden entries.
          if not hidden and name.startswith("."):
            continue

          try:
            is_dir = entry.is_dir(
              follow_symlinks=False
            )

            is_file = entry.is_file(
              follow_symlinks=False
            )

          except OSError:
            continue

          # Directory
          if is_dir:

            # Search result for directories.
            if filter in {"all", "directories"}:
              name_lower = name.lower()

              if not search or search in name_lower:
                entry_path = entry.path

                relative_path = os.path.relpath(
                  entry_path,
                  root_path,
                )

                kikxpath = (
                  f"{directory.rstrip('/')}/{relative_path}"
                )

                try:
                  results.append(
                    get_path_info(
                      Path(entry_path),
                      kikxpath,
                    )
                  )

                except OSError:
                  pass

            # Always continue scanning recursively.
            stack.append(entry.path)

            continue

          # Ignore anything that isn't a file.
          if not is_file:
            continue

          # Filename search.
          if search and search not in name.lower():
            continue

          # Extension.
          suffix = os.path.splitext(name)[1].lower()

          if extension_set and suffix not in extension_set:
            continue

          # Directory-only search.
          if filter == "directories":
            continue

          # Image-only search.
          if filter == "images":
            if suffix not in IMAGE_EXTENSIONS:
              continue

          # File matched.
          relative_path = os.path.relpath(
            entry.path,
            root_path,
          )

          kikxpath = f"{directory.rstrip('/')}/{relative_path}"

          try:
            results.append(
              get_path_info(
                Path(entry.path),
                kikxpath,
              )
            )

          except OSError:
            continue

    except PermissionError:
      logger.debug(
        "Permission denied while searching: %s",
        current,
      )

    except OSError:
      logger.debug(
        "Failed to scan directory: %s",
        current,
      )

  # If unlimited, there is no remaining result limit.
  if max_results == -1:
    has_more = bool(stack)
  else:
    has_more = bool(stack) or len(results) >= max_results

  return {
    "directory": directory,
    "search": search,
    "filter": filter,
    "extension": extensions,
    "count": len(results),
    "max_results": max_results,
    "has_more": has_more,
    "files": results,
  }

# Touch

@srv.router.post("/touch")
def touch(request: Request, path: str):
  file_path = resolve_path(request, path, False)

  try:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.touch(exist_ok=True)

  except OSError:
    srv.exception(500, "Failed to touch file")

  return {
    "path": path,
    "success": True
  }

# Exists

@srv.router.get("/exists")
def exists(request: Request, path: str):
  file_path = resolve_path(request, path, True)

  return {
    "path": path,
    "exists": file_path.exists(),
    "file": file_path.is_file()
    if file_path.exists()
    else False,
    "directory": file_path.is_dir()
    if file_path.exists()
    else False
  }

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

  return srv.ok("File deleted successfully")

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

  return srv.ok("File created successfully")

# Create Directory

@srv.router.post("/create_directory")
def create_directory(request: Request, dir_request: DirectoryCreateRequest) -> dict:
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

  return srv.ok("Directory created successfully")

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
def delete_list_paths(request: Request, payload: DeleteListModel) -> dict:
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

  return srv.ok("Directory deleted successfully")

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

# Stat

@srv.router.get("/stat")
def stat_file(request: Request, path: str):
  file_path = resolve_path(request, path, True)

  if not file_path.exists():
    srv.exception(404, "Path not found")

  try:
    stat = file_path.stat()
  except OSError:
    srv.exception(500, "Failed to read file information")

  return {
    "path": path,
    "name": file_path.name,
    "type": "directory"
    if file_path.is_dir()
    else "file",
    "size": stat.st_size,
    "mode": stat.st_mode,
    "permissions": oct(stat.st_mode & 0o777),
    "uid": stat.st_uid,
    "gid": stat.st_gid,
    "created": _file_timestamp(stat.st_ctime),
    "modified": _file_timestamp(stat.st_mtime),
    "accessed": _file_timestamp(stat.st_atime)
  }

# Disk Usage

@srv.router.get("/disk-usage")
def disk_usage(request: Request, path: str):
  file_path = resolve_path(request, path, True)

  if not file_path.exists():
    srv.exception(404, "Path not found")

  try:
    usage = shutil.disk_usage(str(file_path))
  except OSError:
    srv.exception(500, "Failed to read disk usage")

  return {
    "path": path,
    "total": usage.total,
    "used": usage.used,
    "free": usage.free,
    "available": usage.free,
    "percent": round(
      (usage.used / usage.total) * 100,
      2
    )
    if usage.total
    else 0
  }

# Info

@srv.router.get("/info")
def path_info(request: Request, path: str):
  file_path = resolve_path(request, path, True)

  if not file_path.exists():
    srv.exception(404, "File not found")

  try:
    return get_path_info(file_path, path)
  except PermissionError:
    srv.exception(403, "Permission denied")
  except OSError:
    logger.exception("Failed to get path info: %s", path)
    srv.exception(500, "Failed to get path information")

# Tree
@srv.router.get("/tree")
def tree(
  request: Request,
  directory: str,
  depth: int = 2,
  hidden: bool = True
):
  dir_path = resolve_path(request, directory, True)

  if not dir_path.is_dir():
    srv.exception(404, "Directory not found")

  if depth < 0:
    srv.exception(400, "Invalid depth")

  def build_tree(path, current_depth):
    result = []

    if current_depth > depth:
      return result

    try:
      entries = list(os.scandir(path))
    except OSError:
      return result

    entries.sort(key=lambda item: item.name.lower())

    for entry in entries:
      if (not hidden and entry.name.startswith(".")):
        continue

      try:
        is_dir = entry.is_dir(follow_symlinks=False)

        info = {
          "name": entry.name,
          "path": str(
            Path(directory)
            / Path(entry.path).relative_to(
              dir_path
            )
          ),
          "type": "directory"
          if is_dir
          else "file"
        }

        if is_dir:
          info["children"] = build_tree(
            entry.path,
            current_depth + 1
          )

        result.append(info)

      except OSError:
        continue

    return result

  return {
    "directory": directory,
    "depth": depth,
    "files": build_tree(
      str(dir_path),
      0
    )
  }

# Mime Type

@srv.router.get("/mime")
def mime_type(request: Request, path: str):
  file_path = resolve_path(request, path, True)

  if not file_path.exists():
    srv.exception(404, "Path not found")

  mime, encoding = mimetypes.guess_type(str(file_path))

  if file_path.is_dir():
    mime = "inode/directory"

  return {
    "path": path,
    "mime": mime or "application/octet-stream",
    "encoding": encoding,
    "extension": file_path.suffix.lower()
  }

# Hash

@srv.router.get("/hash")
def hash_file(
  request: Request,
  path: str,
  algorithm: str = "sha256",
  chunk_size: int = 1024 * 1024
):
  file_path = resolve_path(request, path, True)

  if not file_path.exists():
    srv.exception(404, "Path not found")

  if not file_path.is_file():
    srv.exception(400, "Path is not a file")

  algorithm = algorithm.lower()

  try:
    hasher = hashlib.new(algorithm)
  except ValueError:
    srv.exception(400, "Unsupported hash algorithm")

  try:
    with open(file_path, "rb") as file:
      while True:
        chunk = file.read(chunk_size)

        if not chunk:
          break

        hasher.update(chunk)

  except OSError:
    srv.exception(500, "Failed to read file")

  return {
    "path": path,
    "algorithm": algorithm,
    "hash": hasher.hexdigest()
  }

# Checksum

@srv.router.get("/checksum")
def checksum(request: Request, path: str, algorithm: str = "sha256"):
  return hash_file(request, path, algorithm)

# Chmod

@srv.router.post("/chmod")
def chmod_file(request: Request, path: str, mode: str):
  file_path = resolve_path(request, path, False)

  if not file_path.exists():
    srv.exception(404, "Path not found")

  try:
    if mode.startswith("0"):
      permissions = int(mode, 8)
    else:
      permissions = int(mode, 8)

  except ValueError:
    srv.exception(400, "Invalid permission mode")

  if permissions < 0 or permissions > 0o777:
    srv.exception(400, "Invalid permission mode")

  try:
    os.chmod(file_path, permissions)
  except OSError:
    srv.exception(500, "Failed to change permissions")

  return {
    "path": path,
    "mode": oct(permissions),
    "success": True
  }

# Batch

@srv.router.post("/batch")
def batch_operations(request: Request, operations: list[dict] = Body(...)):
  results = []

  for operation in operations:
    action = operation.get("action")

    try:
      if action == "delete":
        path = operation.get("path")

        if not path:
          raise ValueError("Missing path")

        file_path = resolve_path(request, path, False)

        if file_path.is_dir():
          shutil.rmtree(file_path)

        elif file_path.exists():
          file_path.unlink()

        safe_delete_thumbnail(file_path)

        results.append({
          "action": action,
          "path": path,
          "success": True
        })

      elif action == "rename":
        source = operation.get("source")
        new_name = operation.get("new_name")
      
        if not source:
          raise ValueError("Missing source")
      
        if not new_name:
          raise ValueError("Missing new_name")
      
        source_path = resolve_path(request, source, False)
      
        if not source_path.exists():
          raise ValueError("Source not found")
      
        new_name = os.path.basename(str(new_name))
      
        if not new_name or new_name in {".", ".."}:
          raise ValueError("Invalid new_name")
      
        target = (source_path.parent / new_name)
      
        source_path.rename(target)
        
        safe_delete_thumbnail(source_path)
      
        results.append({
          "action": action,
          "source": source,
          "new_name": new_name,
          "path": str(target),
          "success": True
        })

      elif action == "copy":
        source = operation.get("source")
        dest = operation.get("dest")

        if not source:
          raise ValueError("Missing source")

        if not dest:
          raise ValueError("Missing dest")

        source_path = resolve_path(request, source, True)

        dest_path = resolve_path(request, dest, False)

        if not source_path.exists():
          raise ValueError("Source not found")

        if source_path.is_dir():
          shutil.copytree(
            source_path,
            dest_path,
            dirs_exist_ok=True
          )
        else:
          dest_path.parent.mkdir(parents=True, exist_ok=True)

          shutil.copy2(source_path, dest_path)

        results.append({
          "action": action,
          "source": source,
          "dest": dest,
          "success": True
        })

      elif action == "move":
        source = operation.get("source")
        dest = operation.get("dest")

        if not source:
          raise ValueError("Missing source")

        if not dest:
          raise ValueError("Missing dest")

        source_path = resolve_path(request, source, True)

        dest_path = resolve_path(request, dest, False)

        if not source_path.exists():
          raise ValueError("Source not found")

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source_path), str(dest_path))
        
        safe_delete_thumbnail(source_path)

        results.append({
          "action": action,
          "source": source,
          "dest": dest,
          "success": True
        })

      elif action == "touch":
        path = operation.get("path")

        if not path:
          raise ValueError("Missing path")

        file_path = resolve_path(request, path, False)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.touch(exist_ok=True)

        results.append({
          "action": action,
          "path": path,
          "success": True
        })

      else:
        raise ValueError(f"Unknown action: {action}")

    except Exception as error:
      results.append({
        "action": action,
        "success": False,
        "error": str(error)
      })

  return {
    "count": len(results),
    "results": results
  }

# Trash

@srv.router.post("/trash")
def trash(request: Request, path: str):
  file_path = resolve_path(request, path, False)

  if not file_path.exists():
    srv.exception(404, "Path not found")

  if file_path.name == ".kikx-trash":
    srv.exception(400, "Invalid trash path")

  trash_dir = (file_path.parent / ".kikx-trash")

  trash_dir.mkdir(parents=True, exist_ok=True)

  trash_id = uuid.uuid4().hex

  target = (trash_dir / trash_id / file_path.name)

  target.parent.mkdir(parents=True, exist_ok=True)

  metadata = {
    "id": trash_id,
    "name": file_path.name,
    "original_path": str(
      file_path
    ),
    "trashed_at": datetime.now(
      timezone.utc
    ).isoformat()
  }

  try:
    shutil.move(str(file_path), str(target))

    with open(
      target.parent / "metadata.json",
      "w",
      encoding="utf-8"
    ) as file:
      json.dump(metadata, file, indent=2)
    
    safe_delete_thumbnail(file_path)

  except OSError:
    srv.exception(500, "Failed to move file to trash")

  return {
    "success": True,
    "id": trash_id,
    "name": file_path.name
  }

# Restore

@srv.router.post("/restore")
def restore(request: Request, trash_directory: str, trash_id: str):
  trash_path = resolve_path(request, trash_directory, True)

  if not trash_path.is_dir():
    srv.exception(404, "Trash directory not found")

  item_dir = (trash_path / trash_id)

  metadata_path = (item_dir / "metadata.json")

  if not metadata_path.is_file():
    srv.exception(404, "Trash item not found")

  try:
    with open(
      metadata_path,
      "r",
      encoding="utf-8"
    ) as file:
      metadata = json.load(file)

    original_path = Path(metadata["original_path"])

  except Exception:
    srv.exception(500, "Invalid trash metadata")

  if original_path.exists():
    original_path = get_unique_path(original_path)

  item = None

  for child in item_dir.iterdir():
    if child.name != "metadata.json":
      item = child
      break

  if item is None:
    srv.exception(404, "Trash item is empty")

  try:
    original_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(item), str(original_path))

    shutil.rmtree(item_dir, ignore_errors=True)

  except OSError:
    srv.exception(500, "Failed to restore item")

  return {
    "success": True,
    "path": str(original_path),
    "id": trash_id
  }

# Compress

@srv.router.post("/compress")
def compress(
  request: Request,
  source: str,
  destination: str,
  format: str = "zip"
):
  source_path = resolve_path(request, source, True)

  destination_path = resolve_path(request, destination, False)

  if not source_path.exists():
    srv.exception(404, "Source not found")

  format = format.lower()

  try:
    if format == "zip":
      with zipfile.ZipFile(
        destination_path,
        "w",
        zipfile.ZIP_DEFLATED
      ) as archive:

        if source_path.is_file():
          archive.write(
            source_path,
            source_path.name
          )

        else:
          for root, dirs, files in os.walk(source_path):
            root_path = Path(root)

            for filename in files:
              file_path = (root_path / filename)

              archive.write(
                file_path,
                file_path.relative_to(
                  source_path.parent
                )
              )

    elif format in {"tar", "tar.gz", "tgz"}:
      mode = (
        "w:gz"
        if format in {"tar.gz", "tgz"}
        else "w"
      )

      with tarfile.open(destination_path, mode) as archive:
        archive.add(source_path, arcname=source_path.name)

    else:
      srv.exception(400, "Unsupported archive format")

  except OSError:
    srv.exception(500, "Failed to create archive")

  return {
    "success": True,
    "source": source,
    "destination": destination,
    "format": format
  }

# Extract

@srv.router.post("/extract")
def extract(
  request: Request,
  archive: str,
  destination: str
):
  archive_path = resolve_path(request, archive, True)

  destination_path = resolve_path(request, destination, False)

  if not archive_path.is_file():
    srv.exception(404, "Archive not found")

  destination_path.mkdir(parents=True, exist_ok=True)

  suffixes = "".join(archive_path.suffixes).lower()

  try:
    # ZIP
    if archive_path.suffix.lower() == ".zip":

      with zipfile.ZipFile(archive_path, "r") as archive_file:

        members = archive_file.infolist()

        for member in members:
          member_name = member.filename

          if not _safe_archive_member(
            destination_path,
            member_name
          ):
            srv.exception(400, "Unsafe archive path")

        archive_file.extractall(destination_path)

        count = len(members)

    # TAR / TAR.GZ / TGZ
    elif (
      archive_path.suffix.lower() == ".tar"
      or suffixes.endswith(".tar.gz")
      or suffixes.endswith(".tgz")
    ):

      with tarfile.open(
        archive_path,
        "r:*"
      ) as archive_file:

        members = archive_file.getmembers()

        for member in members:
          member_name = member.name

          if not _safe_archive_member(
            destination_path,
            member_name
          ):
            srv.exception(400, "Unsafe archive path")

        archive_file.extractall(
          destination_path,
          filter="data"
        )

        count = len(members)

    else:
      srv.exception(400, "Unsupported archive format")

  except (zipfile.BadZipFile, tarfile.TarError):
    srv.exception(400, "Invalid archive")

  except OSError:
    srv.exception(500, "Failed to extract archive")

  return {
    "success": True,
    "archive": archive,
    "destination": destination,
    "count": count
  }

# Watch

def _watch_path(
  directory,
  relative_path,
  dir_path,
  path_type="virtual"
):
  absolute_path = (Path(dir_path) / relative_path).resolve()

  if path_type == "absolute":
    return str(absolute_path)

  return (
    f"{directory.rstrip('/')}/"
    f"{relative_path.replace(os.sep, '/')}"
  )

@srv.router.get("/watch")
def watch(
  request: Request,
  directory: str,
  interval: float = 1.0,
  path_type: str = "virtual"
):
  dir_path = resolve_path(request, directory, True)

  if not dir_path.is_dir():
    srv.exception(404, "Directory not found")

  interval = max(0.2, min(interval, 10))

  def event_stream():
    previous = _directory_snapshot(dir_path)

    while True:
      time.sleep(interval)

      try:
        current = _directory_snapshot(dir_path)

        added = [
          _watch_path(
            directory,
            path,
            dir_path,
            path_type
          )
          for path in current
          if path not in previous
        ]

        removed = [
          _watch_path(
            directory,
            path,
            dir_path,
            path_type
          )
          for path in previous
          if path not in current
        ]

        changed = [
          _watch_path(
            directory,
            path,
            dir_path,
            path_type
          )
          for path in current
          if (
            path in previous
            and current[path] != previous[path]
          )
        ]

        if added or removed or changed:
          data = json.dumps({
            "directory": directory,
            "path_type": path_type,
            "added": added,
            "removed": removed,
            "changed": changed
          })

          yield (
            f"event: change\n"
            f"data: {data}\n\n"
          )

        else:
          yield ": heartbeat\n\n"

        previous = current

      except Exception as error:
        logger.debug(
          "Watch error: %s",
          error
        )

        yield (
          "event: error\n"
          "data: {\"error\":true}\n\n"
        )

  return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no"
    }
  )

# Convert Path

@srv.router.get("/convert-path")
def convert_path_route(
  request: Request,
  path: str,
  type: str = "virtual"
):
  converted = convert_path(request, path, type)

  return {
    "path": path,
    "type": type,
    "converted": converted
  }

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