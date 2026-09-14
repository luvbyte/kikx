from fastapi import APIRouter, Depends

from lib.utils import file_response

from . import get_core


router = APIRouter()


# ---------------------- Public App
@router.get("/app/{name}/{path:path}")
async def public_app_route(
  name: str,
  path: str,
  core=Depends(get_core),
):
  """Return a public file for the given app."""
  response = file_response(
    core.config.apps_path,
    name,
    "public",
    path,
  )

  # Cache for 10 minutes
  response.headers["Cache-Control"] = "public, max-age=600"

  return response