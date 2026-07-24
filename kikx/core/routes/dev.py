from fastapi import APIRouter, Request, Depends
from fastapi.responses import FileResponse

from core.utils import kikx_core_info_dump
from pathlib import Path

router = APIRouter()

# Get core
def get_core(request: Request):
  return request.app.state.core

# ------------------
@router.get("core-info-dump")
def dump_core_info(core = Depends(get_core)):
  return kikx_core_info_dump(core)

# ------------------
@router.get("/{path:path}")
def serve(path: str):
  if len(path.strip()) <= 0:
    path = "index.html"

  return FileResponse(Path("web", "dev", path))

