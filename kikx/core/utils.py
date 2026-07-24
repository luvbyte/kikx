from fastapi import HTTPException

from typing import Any
from core.models.app_models import AppManifestModel

from lib.parser import parse_config



# App manifest
def load_app_manifest(core: Any, name: str, raw: bool = False, both: bool = False) -> Any:
  manifest_path = (core.config.apps_path / name / "app.json").resolve()
  
  if not manifest_path.exists():
    raise HTTPException(status_code=404, detail="File not found")

  # checking relative paths
  if not manifest_path.is_relative_to(core.config.apps_path):
    raise HTTPException(status_code=403, detail="Forbidden path")

  manifest = parse_config(manifest_path, AppManifestModel)

  if name != manifest.name:
    raise HTTPException(status_code=404, detail="App manifest mismatch name")

  info = {
    "name": name,
    "title": manifest.title,
    "icon": f"/public/app/{name}/{manifest.icon}",
    "theme": manifest.theme
  }

  if both:
    return info, manifest

  # Parsing file
  if raw:
    return manifest
  
  return info

# Full core info 
def kikx_core_info_dump(core) -> dict[str, Any]:
  return {
    "meta": {
      "version": core.version,
      "author": core.author,
      "dev_mode": core.is_dev_mode
    },
    "config": core.config.info(),
    "services": core.services.info(),
    "auth": core.auth.info(),
    "user": core.user.info(),
    "clients": { name: c.info() for name, c in core.clients.items() },
    "app_index": core.app_index,
    "events": core.events.info(),
    "apps": {
      "admin_apps": core.get_admin_apps_list(),
      "installed": core.get_installed_apps(both=True)
    }
  }
