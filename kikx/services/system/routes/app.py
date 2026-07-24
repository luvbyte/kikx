import json
import shutil
import logging
import asyncio
import tempfile

from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from lib.hash import hash_file
from lib.utils import file_response
from core.kpm import AppInstaller, AppUninstaller
from core.setup.pkg import parse_github_repo, extract_package, fetch_release_package

from fastapi import APIRouter, Request, UploadFile, File, Depends


logger = logging.getLogger(__name__)


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

  client, app = srv.get_client_or_app(request)
  if app is None: # allow access for clients
    return core

  # If app - check kpm exists in app config
  if not app.config.system.check("kpm") or not app.config.sudo:
    srv.exception(403, "Require 'kpm' permission")

  return core

def get_or_extract(raw_temp: Path, temp_dir: Path) -> Path:
  dirs = [p for p in temp_dir.iterdir() if p.is_dir()]

  if len(dirs) == 1:
    return dirs[0]

  return extract_package(raw_temp, temp_dir)

@router.get("/installed-apps")
async def get_installed_apps(app_name: Optional[str] = None, core = Depends(check_permisson)):
  return core.get_installed_apps(raw=True)

# ------------- Prepare Local Install By UploadFile
@router.post("/prepare-install")
async def prepare_install(file: UploadFile = File(...), core = Depends(check_permisson)):
  srv = router.get_srv()
  
  upload_dir = Path(tempfile.mkdtemp())

  try:
    if not file.filename.endswith(".kikx"):
      srv.exception(403, "Only .kikx packages are supported")

    raw_temp = upload_dir / file.filename

    with open(raw_temp, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)
    
    await file.close()
    
    file_hash = hash_file(raw_temp)
    
    temp_dir = Path(tempfile.gettempdir()) / f"kikx_{file_hash}"
    temp_dir.mkdir(parents=True, exist_ok=True)
  
    # removing source if found for local install
    source_file = temp_dir / ".source_data.json"
    source_file.unlink(missing_ok=True)

    # Extract only if not already extracted
    extracted_path = get_or_extract(raw_temp, temp_dir)
    
    installer = AppInstaller(core, extracted_path)
  
    return {
      "temp_id": file_hash,
      "manifest": installer.get_app_manifest(),
      "is_update": installer.is_update,
      "app_installed": installer.is_app_installed,
      "is_compatible": installer.is_compatible
    }
  except Exception as e:
    logger.exception(e)
    srv.exception(403, e)
  finally:
    shutil.rmtree(upload_dir, ignore_errors=True)

# ------------- Prepare Github Install
# Optimize make fast
@router.post("/prepare-github")
async def prepare_install_github(
  repo_url: str,
  tag: str | None = None,
  core=Depends(check_permisson)
):
  srv = router.get_srv()
  
  download_dir = Path(tempfile.mkdtemp())

  try:
    owner, repo = parse_github_repo(repo_url)

    release, raw_temp = await fetch_release_package(download_dir, owner, repo, tag)

    # Hash
    file_hash = hash_file(raw_temp)
  
    temp_dir = Path(tempfile.gettempdir()) / f"kikx_{file_hash}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = get_or_extract(raw_temp, temp_dir)

    source = {
      "url": repo_url,
      "owner": owner,
      "repo": repo,
      "tag": release.get("tag_name"),
      "hash": file_hash
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
  except Exception as e:
    logger.exception(e)
    srv.exception(403, e)
  finally:
    shutil.rmtree(download_dir, ignore_errors=True)

# ------------- Preview App By TempID
@router.get("/preview/{temp_id}/{path:path}")
async def get_file(temp_id: str, path: str):
  srv = router.get_srv()

  try:
    temp_dir = Path(tempfile.gettempdir()) / f"kikx_{temp_id}"
  
    if not temp_dir.exists():
      srv.exception(404, "Package not found")

    extracted_path = next(p for p in temp_dir.iterdir() if p.is_dir())

    return file_response(extracted_path, path)

  except Exception as e:
    srv.exception(403, e)

# ------------- Confirm Install After Preview
@router.post("/confirm-install")
async def confirm_install(request: Request, temp_id: str, core = Depends(check_permisson)):
  srv = router.get_srv()

  try:
    temp_dir = Path(tempfile.gettempdir()) / f"kikx_{temp_id}"

    if not temp_dir.exists():
      srv.exception(404, "Install session not found")

    extracted_dirs = [p for p in temp_dir.iterdir() if p.is_dir()]
    if len(extracted_dirs) != 1:
      srv.exception(403, "Corrupted session")

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
  except Exception as e:
    logger.exception(e)
    srv.exception(403, e)

# ------------- Cancel Install and Cleanup
@router.post("/cancel-install")
async def cancel_install(temp_id: str, _ = Depends(check_permisson)):
  srv = router.get_srv()

  try:
    base_tmp = Path(tempfile.gettempdir()).resolve()
    temp_dir = (base_tmp / f"kikx_{temp_id}").resolve()

    if not temp_dir.exists():
      return srv.ok("already_cancelled")

    # critical safety check
    if not temp_dir.is_relative_to(base_tmp):
      srv.exception(403, "Forbidden path")

    shutil.rmtree(temp_dir, ignore_errors=True)

    return srv.ok()

  except Exception as e:
    logger.exception(e)
    srv.exception(403, e)

# ------------- Uninstall App
@router.delete("/uninstall")
async def uninstall_app_route(app_name: str, core = Depends(check_permisson)):
  srv = router.get_srv()

  try:
    AppUninstaller(core, app_name).uninstall()
    
    # async Broadcast to all clients
    asyncio.create_task(core.broadcast_to_clients("app:uninstalled", {
      "name": app_name
    }))

    return srv.ok()

  except Exception as e:
    logger.exception(e)
    srv.exception(403, e)

