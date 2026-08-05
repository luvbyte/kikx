from fastapi import APIRouter, HTTPException, Depends

from core.utils import load_app_manifest
from pydantic import BaseModel, Field

from . import get_core


router = APIRouter()



class AppsListModel(BaseModel):
  client_id: str = Field(..., description="Client ID")


@router.post("/apps/list")
def get_apps_list(data: AppsListModel, core = Depends(get_core)):
  client = core.clients.get(data.client_id)
  if client is None:
    raise HTTPException(401, "Client not found")
    
  return core.get_installed_apps()

@router.get("/ui-list")
def get_ui_list(core = Depends(get_core)):
  return {
    "ui": list(core.auth.user_config.ui),
    "default": core.auth.user_config.default_ui
  }
