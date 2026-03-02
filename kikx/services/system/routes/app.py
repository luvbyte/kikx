import json
import uuid
import httpx
import shutil
import asyncio
import tempfile
import subprocess

from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from lib.hash import hash_file
from urllib.parse import urlparse
from core.kpm import GITHUB_API, AppInstaller, AppUninstaller, resolve_app_package, parse_github_repo

from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse



class AppInstallRoute(BaseModel):
  uri: Optional[str] = None 


class ServiceRouter(APIRouter):
  def __init__(self):
    super().__init__()
    self._srv = None

  def get_srv(self):
    return self._srv


router = ServiceRouter()


# Check authorization & rerurn code
def check_permisson(request: Request):
  srv = router.get_srv()
  core = srv.get_core()
  
  return core # remove 

  client, app = srv.get_client_or_app(request)
  if app is None: # allow access for clients
    return core

  # If app - check kpm exists in app config
  if not app.config.system.check("kpm"):
    raise HTTPException(403, "Permission denied")

  return core

# Installed app manifest 
def get_installed_app(app_name, core):
  return core.user.load_app_manifest(app_name)

# Return apps / app
@router.get("/installed-apps")
async def get_installed_apps(app_name: Optional[str] = None, core = Depends(check_permisson)):
  try:
    if app_name is None:
      return [get_installed_app(name, core) for name in core.user.get_installed_apps()]
    
    return get_installed_app(app_name, core)
  except Exception as e:
    raise HTTPException(status_code=404, detail=str(e))


@router.post("/prepare-install")
async def prepare_install(file: UploadFile = File(...), core = Depends(check_permisson)):
  if not file.filename.endswith(".kikx"):
    raise HTTPException(400, "Only .kikx packages are supported")

  raw_temp = Path(tempfile.mkdtemp()) / file.filename

  with open(raw_temp, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)

  file_hash = hash_file(raw_temp)

  temp_dir = Path(tempfile.gettempdir()) / f"kikx_{file_hash}"
  temp_dir.mkdir(parents=True, exist_ok=True)

  # removing source if found for local installs
  source_file = temp_dir / ".source_data.json"
  source_file.unlink(missing_ok=True)

  # Extract only if not already extracted
  if not any(temp_dir.iterdir()):
    extracted_path = resolve_app_package(raw_temp, temp_dir)
  else:
    extracted_path = next(p for p in temp_dir.iterdir() if p.is_dir())

  installer = AppInstaller(core, extracted_path)

  return {
    "temp_id": file_hash,
    "manifest": installer.get_app_manifest(),
    "is_update": installer.is_update,
    "app_installed": installer.is_app_installed,
    "is_compatible": installer.is_compatible
  }

@router.get("/preview/{temp_id}/{path:path}")
async def get_file(temp_id: str, path: str):
  temp_dir = Path(tempfile.gettempdir()) / f"kikx_{temp_id}"

  if not temp_dir.exists():
    raise HTTPException(404, "Package not found")

  extracted_path = next(p for p in temp_dir.iterdir() if p.is_dir())

  requested_path = (extracted_path / path).resolve()

  # Prevent path traversal
  if not str(requested_path).startswith(str(extracted_path.resolve())):
    raise HTTPException(403, "Access denied")

  if not requested_path.exists() or not requested_path.is_file():
    raise HTTPException(404, "File not found")

  return FileResponse(requested_path)

@router.post("/confirm-install")
async def confirm_install(request: Request, temp_id: str, core = Depends(check_permisson)):
  srv = router.get_srv()
  core = srv.get_core()

  temp_dir = Path(tempfile.gettempdir()) / f"kikx_{temp_id}"

  if not temp_dir.exists():
    raise HTTPException(404, "Install session not found")

  extracted_dirs = [p for p in temp_dir.iterdir() if p.is_dir()]
  if len(extracted_dirs) != 1:
    raise HTTPException(400, "Corrupted session")

  source_file = temp_dir / ".source_data.json"

  if not source_file.exists():
    source = "local"
  else:
    source = json.loads(source_file.read_text())

  installer = AppInstaller(core, extracted_dirs[0])

  result = installer.install(source)

  # async Broadcast to all clients
  asyncio.create_task(core.broadcast_to_clients("app:installed", installer.get_manifest()))

  shutil.rmtree(temp_dir, ignore_errors=True)

  return {"res": "ok", "result": result}

@router.post("/cancel-install")
async def cancel_install(temp_id: str):
  base_tmp = Path(tempfile.gettempdir()).resolve()
  temp_dir = (base_tmp / f"kikx_{temp_id}").resolve()

  if not temp_dir.exists():
    return {"res": "already_cancelled"}

  # critical safety check
  if not temp_dir.is_relative_to(base_tmp):
    raise HTTPException(400, "Unsafe path")

  shutil.rmtree(temp_dir, ignore_errors=True)

  return {"res": "cancelled"}


@router.delete("/uninstall")
async def uninstall_app_route(app_name: str, core = Depends(check_permisson)):
  try:
    AppUninstaller(core, app_name).uninstall()
  
    return { "res": "ok" }
  except Exception as e:
    raise HTTPException(status_code=401, detail=str(e))

@router.post("/prepare-github")
async def prepare_install_github(
  repo_url: str,
  tag: str | None = None,
  core=Depends(check_permisson)
):
  owner, repo = parse_github_repo(repo_url)

  # Select correct release URL
  if tag:
    url = f"{GITHUB_API}/{owner}/{repo}/releases/tags/{tag}"
  else:
    url = f"{GITHUB_API}/{owner}/{repo}/releases/latest"

  headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/122.0.0.0 Safari/537.36"
    ),
  }

  async with httpx.AsyncClient(follow_redirects=True) as client:
    resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
      raise HTTPException(404, f"Release not found ({resp.status_code})")

    release = resp.json()

  # Find .kikx asset
  kikx_asset = next(
    (a for a in release.get("assets", []) if a["name"].endswith(".kikx")),
    None
  )

  if not kikx_asset:
    raise HTTPException(400, "No .kikx asset found in release")

  download_url = kikx_asset["browser_download_url"]

  # Download asset
  raw_temp = Path(tempfile.mkdtemp()) / kikx_asset["name"]

  async with httpx.AsyncClient(follow_redirects=True) as client:
    async with client.stream("GET", download_url, headers=headers) as r:
      r.raise_for_status()
      with open(raw_temp, "wb") as f:
        async for chunk in r.aiter_bytes():
          f.write(chunk)

  # Hash
  file_hash = hash_file(raw_temp)

  temp_dir = Path(tempfile.gettempdir()) / f"kikx_{file_hash}"
  temp_dir.mkdir(parents=True, exist_ok=True)

  if not any(temp_dir.iterdir()):
    extracted_path = resolve_app_package(raw_temp, temp_dir)
  else:
    extracted_path = next(p for p in temp_dir.iterdir() if p.is_dir())

  source = {
    "url": repo_url,
    "owner": owner,
    "repo": repo,
    "tag": release.get("tag_name"),
  }

  (temp_dir / ".source_data.json").write_text(json.dumps(source))

  installer = AppInstaller(core, extracted_path)
  
  # If app installed - then return that source
  if installer.is_app_installed:
    source = installer.get_source()

  return {
    "temp_id": file_hash,
    "manifest": installer.get_app_manifest(),
    "source": source,
    "is_update": installer.is_update,
    "app_installed": installer.is_app_installed,
    "is_compatible": installer.is_compatible
  }
