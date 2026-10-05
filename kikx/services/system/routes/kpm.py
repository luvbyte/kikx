import asyncio
import json
import logging
import shutil
import tempfile

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from lib.hash import hash_file
from lib.utils import file_response, generate_uuid, joinpath

from core.kpm import AppInstaller, AppUninstaller
from core.setup.pkg import (
  extract_package,
  fetch_release_package,
  parse_github_repo,
)
from core.utils import load_app_manifest


logger = logging.getLogger(__name__)


# ---------------------- Models
class AppInstallRoute(BaseModel):
  uri: str | None = None


# ---------------------- Utils
def get_or_extract(raw_temp: Path, temp_dir: Path) -> Path:
  dirs = [path for path in temp_dir.iterdir() if path.is_dir()]

  if len(dirs) == 1:
    return dirs[0]

  return extract_package(raw_temp, temp_dir)


def clean_temp_id(temp_id: str) -> None:
  temp_dir = joinpath(
    tempfile.gettempdir(),
    f"kikxapp_{temp_id}",
  )

  shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------- Service Router
class ServiceRouter(APIRouter):
  def __init__(self) -> None:
    super().__init__()
    self._srv = None
    self._temp_maps: dict = {}

  def _prepare_map(
    self,
    temp_id: str,
    _id: str,
    _type: str,
    source: str | dict,
  ):
    self._temp_maps[temp_id] = {
      "id": _id,
      "type": _type,
      "source": source,
    }

  async def clean_temp(
    self,
    _id: str,
    _type: str,
  ):
    temp_ids = [
      uid
      for uid, value in self._temp_maps.items()
      if value["type"] == _type and value["id"] == _id
    ]

    for uid in temp_ids:
      try:
        await asyncio.to_thread(clean_temp_id, uid)
      finally:
        self._temp_maps.pop(uid, None)

  async def on_close_app(self, app_id: str):
    await self.clean_temp(app_id, "app")

  async def on_close_client(self, client_id: str):
    await self.clean_temp(client_id, "client")

  def _on_router_init(self, core):
    core.events.add_event("app:close", self.on_close_app)
    core.events.add_event("client:close", self.on_close_client)

  def on_router_init(self, srv):
    srv.add_event("startup", self._on_router_init)

  def get_srv(self):
    return self._srv


router = ServiceRouter()


# ---------------------- Permission
def check_permission(request: Request):
  srv = router.get_srv()
  core = srv.get_core()

  client, app = srv.get_client_or_app(request)

  # Clients are allowed to access KPM.
  if app is None:
    return core

  # Apps must have the KPM permission.
  if not app.config.system.check("kpm"):
    srv.exception(403, "Require 'kpm' permission")

  return core


# ---------------------- Installed Apps
@router.get("/installed-apps")
def get_installed_apps(core=Depends(check_permission)):
  return core.get_installed_apps(raw=True)


@router.get("/app-info")
def get_app_info(name: str, core=Depends(check_permission)):
  srv = router.get_srv()

  meta, manifest = load_app_manifest(
    srv.get_core(),
    name,
    both=True,
  )

  return {
    "meta": meta,
    "manifest": manifest,
  }


# ---------------------- Prepare Local Install
async def _prepare_install(
  request: Request,
  raw_temp: Path,
  core,
  *,
  source: str = "local",
):
  srv = router.get_srv()
  client, app = srv.get_client_or_app(request)

  uid = generate_uuid()
  file_hash = hash_file(raw_temp)

  temp_dir = Path(tempfile.gettempdir()) / f"kikxapp_{uid}"
  temp_dir.mkdir(parents=True, exist_ok=True)

  # Remove old source metadata before preparing the package.
  (temp_dir / ".source_data.json").unlink(missing_ok=True)

  extracted_path = get_or_extract(raw_temp, temp_dir)

  installer = AppInstaller(core, extracted_path)

  router._prepare_map(
    uid,
    app.id if app else client.id,
    "app" if app else "client",
    source=source,
  )

  return {
    "temp_id": uid,
    "hash": file_hash,
    "manifest": installer.get_app_manifest(),
    "is_update": installer.is_update,
    "app_installed": installer.is_app_installed,
    "is_compatible": installer.is_compatible,
  }


@router.post("/prepare-local")
async def prepare_install_local_app(
  request: Request,
  file: UploadFile = File(...),
  core=Depends(check_permission),
):
  srv = router.get_srv()
  upload_dir = Path(tempfile.mkdtemp())

  try:
    if not file.filename or not file.filename.lower().endswith(".kikx"):
      srv.exception(403, "Only .kikx packages are supported")

    raw_temp = upload_dir / file.filename

    with raw_temp.open("wb") as buffer:
      shutil.copyfileobj(file.file, buffer)

    await file.close()

    return await _prepare_install(
      request,
      raw_temp,
      core,
      source="local",
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Failed to prepare local app")
    srv.exception(500, e)
  finally:
    shutil.rmtree(upload_dir, ignore_errors=True)


@router.post("/prepare-storage")
async def prepare_install_storage_app(
  request: Request,
  path: str = Query(...),
  core=Depends(check_permission),
):
  srv = router.get_srv()

  try:
    # if not path.startswith("home://") || path.startswith("os://") || path.startswith("osr"):
    #   srv.exception(400, f"Invalid path: {path}")

    source = core.config.resolve_path(path)

    if not source.is_file():
      srv.exception(404, f"File not found: {path}")

    if source.suffix.lower() != ".kikx":
      srv.exception(403, "Only .kikx packages are supported")

    return await _prepare_install(
      request,
      source,
      core,
      source="local",
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Failed to prepare storage app")
    srv.exception(500, e)


# ---------------------- Prepare GitHub Install
@router.post("/prepare-github")
async def prepare_install_github_app(
  url: str,
  request: Request,
  tag: str | None = None,
  core=Depends(check_permission),
):
  srv = router.get_srv()
  client, app = srv.get_client_or_app(request)

  download_dir = Path(tempfile.mkdtemp())

  try:
    owner, repo = parse_github_repo(url)

    release, raw_temp = await fetch_release_package(
      download_dir,
      owner,
      repo,
      tag,
    )

    uid = generate_uuid()
    file_hash = hash_file(raw_temp)

    temp_dir = Path(tempfile.gettempdir()) / f"kikxapp_{uid}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = get_or_extract(
      raw_temp,
      temp_dir,
    )

    source = {
      "url": url,
      "owner": owner,
      "repo": repo,
      "tag": release.get("tag_name"),
      "hash": file_hash,
    }

    (temp_dir / ".source_data.json").write_text(
      json.dumps(source),
    )

    installer = AppInstaller(core, extracted_path)

    # Use the installed app source when this is an update.
    if installer.is_app_installed:
      source = installer.get_source()

    router._prepare_map(
      uid,
      app.id if app else client.id,
      "app" if app else "client",
      source=source,
    )

    return {
      "temp_id": uid,
      "hash": file_hash,
      "manifest": installer.get_app_manifest(),
      "source": source,
      "is_update": installer.is_update,
      "app_installed": installer.is_app_installed,
      "is_compatible": installer.is_compatible,
    }

  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Failed to prepare GitHub app")
    srv.exception(500, e)
  finally:
    shutil.rmtree(download_dir, ignore_errors=True)


# ---------------------- Confirm Install
@router.post("/confirm-install")
async def confirm_install_app(
  request: Request,
  temp_id: str,
  core=Depends(check_permission),
):
  srv = router.get_srv()

  try:
    temp_dir = Path(tempfile.gettempdir()) / f"kikxapp_{temp_id}"

    if not temp_dir.exists():
      srv.exception(404, "Install session not found")

    extracted_dirs = [
      path
      for path in temp_dir.iterdir()
      if path.is_dir()
    ]

    if len(extracted_dirs) != 1:
      srv.exception(403, "Corrupted session")

    source_file = temp_dir / ".source_data.json"

    if source_file.exists():
      source = json.loads(source_file.read_text())
    else:
      source = "local"

    installer = AppInstaller(
      core,
      extracted_dirs[0],
    )

    result = installer.install(source)

    # Notify all connected clients after installation.
    asyncio.create_task(
      core.broadcast_to_clients(
        "app:installed",
        installer.get_manifest(),
      )
    )

    shutil.rmtree(temp_dir, ignore_errors=True)

    return {
      "res": "ok",
      "result": result,
    }

  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Failed to confirm app installation")
    srv.exception(500, e)


# ---------------------- Uninstall App
@router.get("/uninstall")
async def uninstall_app(
  app_name: str,
  keep_data: bool = False,
  core=Depends(check_permission),
):
  srv = router.get_srv()

  try:
    AppUninstaller(core, app_name).uninstall(keep_data)

    # Notify all connected clients after uninstalling.
    asyncio.create_task(
      core.broadcast_to_clients(
        "app:uninstalled",
        {
          "name": app_name,
        },
      )
    )

    return srv.ok()

  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Failed to uninstall app: %s", app_name)
    srv.exception(500, e)


# ---------------------- Preview Package
@router.get("/preview/{temp_id}/{path:path}")
def get_file(
  temp_id: str,
  path: str,
):
  srv = router.get_srv()

  try:
    temp_dir = Path(tempfile.gettempdir()) / f"kikxapp_{temp_id}"

    if not temp_dir.exists():
      srv.exception(404, "Package not found")

    extracted_path = next(
      path
      for path in temp_dir.iterdir()
      if path.is_dir()
    )

    return file_response(
      extracted_path,
      path,
    )

  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Failed to preview package")
    srv.exception(500, e)