from fastapi import HTTPException

from typing import Any
from core.models.app_models import AppManifestModel

from lib.parser import parse_config
from lib.utils import is_safe_path



# App manifest
def load_app_manifest(core: Any, name: str, raw: bool = False, both: bool = False) -> Any:
  manifest_path = (core.config.apps_path / name / "app.json").resolve()
  
  if not manifest_path.is_file():
    raise HTTPException(404, "App manifest not found")

  # Safe checking
  if not is_safe_path(core.config.apps_path / name, manifest_path):
    raise HTTPException(403, "Forbidden path")

  manifest = parse_config(manifest_path, AppManifestModel)

  if name != manifest.name:
    raise HTTPException(404, "App manifest name mismatch")

  info = {
    "name": name,
    "title": manifest.title,
    "icon": f"/public/app/{name}/{manifest.icon}",
    "splash": f"/public/app/{name}/{manifest.splash}" if manifest.splash else None,
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
