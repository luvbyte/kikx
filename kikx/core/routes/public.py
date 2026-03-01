from fastapi import APIRouter, HTTPException, Depends
from lib.utils import file_response

from . import get_core


# /public router
router = APIRouter()



@router.get("/app/{name}/{path:path}")
async def public_app_route(name: str, path: str, core = Depends(get_core)):
  """Return a public static file for the given app."""
  return file_response(core.config.apps_path, name, "public", path)

@router.get("/ui/{name}/{path:path}")
async def public_ui_route(name: str, path: str, core = Depends(get_core)):
  """Return a public static file for the given ui."""
  return file_response(core.config.uis_path, name, "public", path)

