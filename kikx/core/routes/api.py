from fastapi import APIRouter, HTTPException, Depends

from core.utils import load_app_manifest
from core.models.app_models import AppsListModel

from . import get_core


router = APIRouter()


@router.post("/apps/list")
def get_apps_list(data: AppsListModel, core = Depends(get_core)):
  client = core.clients.get(data.client_id)
  if client is None:
    raise HTTPException(status_code=401, detail="Client not found")
  
  def safe_load(name):
    try:
      return load_app_manifest(core, name)
    except Exception:
      return None
  
  return [res for name in client.user.get_installed_apps() if (res := safe_load(name)) is not None]

@router.get("/ui-list")
def get_ui_list(core = Depends(get_core)):
  return {
    "ui": list(core.auth.user_config.ui),
    "default": core.auth.user_config.default_ui
  }

@router.get("/app/config")
def get_app_config(app_id: str, core = Depends(get_core)):
  client, app = core.get_client_app_by_id(app_id)
  if client is None or app is None:
    raise HTTPException(status_code=401, detail="Unauthorized")
  
  return client.get_app_config(app)
