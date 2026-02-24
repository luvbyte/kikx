from fastapi import HTTPException
from lib.parser import parse_config
from core.models.app_models import AppManifestModel

# App manifest
def load_app_manifest(core, name: str):
  manifest_path = (core.config.apps_path / name / "app.json").resolve()
  if not manifest_path.exists():
    raise HTTPException(status_code=404, detail="File not found")

  # checking relative paths
  if not manifest_path.is_relative_to(core.config.apps_path):
    raise HTTPException(status_code=403, detail="Forbidden path")

  # Parsing file
  manifest = parse_config(manifest_path, AppManifestModel)

  return {
    "name": name,
    "title": manifest.title,
    "icon": f"/public/app/{name}/{manifest.icon}",

    "theme": manifest.theme
  }

