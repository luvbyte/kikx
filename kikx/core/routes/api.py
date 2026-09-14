from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import get_core


router = APIRouter()


# ---------------------- Models
class AppsListModel(BaseModel):
  client_id: str = Field(
    ...,
    description="Client ID",
  )


# ---------------------- Apps
@router.post("/apps/list")
def get_apps_list(
  data: AppsListModel,
  core=Depends(get_core),
):
  client = core.clients.get(data.client_id)

  if client is None:
    raise HTTPException(401, "Client not found")

  return core.get_installed_apps()


# ---------------------- UI
@router.get("/ui-list")
def get_ui_list(core=Depends(get_core)):
  return {
    "ui": list(core.user.get_installed_uis()),
    "default": core.auth.config.ui,
  }