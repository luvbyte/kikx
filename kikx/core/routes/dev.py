from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from core.utils import kikx_core_info_dump


router = APIRouter()


# ---------------------- Core
def get_core(request: Request):
  return request.app.state.core


# ---------------------- Auth
@router.get("/lazy-login", tags=["Auth"])
def lazy_login(
  key: str,
  ui: str,
  core=Depends(get_core),
):
  if not core.user.is_ui_exists(ui):
    raise HTTPException(404, "UI not found")

  access_token = core.auth.generate_access_token(key, ui)

  response = RedirectResponse("/")
  response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    samesite="strict",
  )

  return response


@router.get("/generate", tags=["Auth"])
def generate(
  key: str,
  ui: str,
  core=Depends(get_core),
):
  if not core.user.is_ui_exists(ui):
    raise HTTPException(404, "UI not found")

  access_token = core.auth.generate_access_token(key, ui)

  return {"access_token": access_token}


# ---------------------- Core Info
@router.get("/core-info-dump")
def dump_core_info(core=Depends(get_core)):
  return kikx_core_info_dump(core)


# ---------------------- Web
@router.get("/{path:path}")
def serve(path: str):
  if not path.strip():
    path = "index.html"

  return FileResponse(Path("web", "dev", path))