from fastapi import APIRouter, Request, Depends

from pydantic import BaseModel
from typing import Any

from core.models.kikx import KikxConfigModel


from . import get_core

class UpdateSettingsModel(BaseModel):
  settings: KikxConfigModel


router = APIRouter()


@router.get("/settings")
def get_settings(reset: bool = False, core = Depends(get_core)):
  return core.get_settings(reset=reset)

@router.post("/settings")
def update_settings(payload: UpdateSettingsModel, core = Depends(get_core)):
  return core.update_settings(payload.settings)

@router.get("/status")
def status(core = Depends(get_core)):
  return core.get_status()

@router.get("/kikx/start")
async def kikx_start(core = Depends(get_core)):
  return await core.start_kikx_server()

@router.get("/kikx/stop")
async def kikx_stop(core = Depends(get_core)):
  return await core.stop_kikx_server()

@router.get("/kikx/stdout")
def get_kikx_stdout(core = Depends(get_core)):
  return core.get_kikx_stdout()

