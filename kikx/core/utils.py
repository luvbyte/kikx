from typing import Any

from fastapi import HTTPException

from core.models.app import AppManifestModel

from lib.parser import parse_config
from lib.utils import joinpath


# App manifest
def load_app_manifest(core: Any, name: str, raw: bool = False, both: bool = False) -> Any:
  manifest_path = joinpath(core.config.apps_path, name, "app.json")

  if not manifest_path.is_file():
    raise HTTPException(404, "App manifest not found")

  manifest = parse_config(manifest_path, AppManifestModel)

  if name != manifest.name:
    raise HTTPException(404, "App manifest name mismatch")

  system_apps = core.get_admin_apps_list()

  meta = {
    "name": name,
    "title": manifest.title,
    "version": manifest.version,
    "author": manifest.author,
    "icon": f"/public/app/{name}/{manifest.icon}",
    "splash": f"/public/app/{name}/{manifest.splash}" if manifest.splash else None,
    "theme": manifest.theme,
    "system": name in system_apps
  }

  if both:
    return meta, manifest

  if raw:
    return manifest

  return meta


# Full core info
def kikx_core_info_dump(core) -> dict[str, Any]:
  return {
    "meta": {
      "version": core.version,
      "author": core.author,
      "dev_mode": core.is_dev_mode
    },
    "config": core.config.info(),
    # "services": core.services.info(),
    "auth": core.auth.info(),
    # "user": core.user.info(),
    "clients": {name: c.info() for name, c in core.clients.items()},
    "app_index": core.app_index,
    "events": core.events.info(),
    "apps": {
      "admin_apps": core.get_admin_apps_list(),
      "installed": core.get_installed_apps(both=True)
    }
  }