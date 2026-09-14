from config.setup import PRE_INSTALL_APPS
from core.kpm import AppInstaller
from core.utils import load_app_manifest

from .pkg import fetch_from_github, is_outdated


# ---------------------- App Actions
async def _apply_app(core, url, name, tag, method):
  def callback(extracted_path, source):
    getattr(AppInstaller(core, extracted_path), method)(source)

  await fetch_from_github(url, name, callback, tag=tag)


async def install_app(core, url, name, tag):
  await _apply_app(core, url, name, tag, "install")


async def update_app(core, url, name, tag):
  await _apply_app(core, url, name, tag, "update")


# ---------------------- Precheck
async def pre_check_apps(core) -> None:
  installed_apps = set(core.user.get_installed_apps())

  for name, (url, tag, required) in PRE_INSTALL_APPS.items():
    is_installed = name in installed_apps

    try:
      if is_installed:
        manifest = load_app_manifest(core, name, raw=True)

        if not is_outdated(manifest.version, tag):
          continue

        core.scr.warning(f"App: {name} outdated. Updating...")
        await update_app(core, url, name, tag)
        core.scr.success(f"App Updated: ({name}) {manifest.version} -> {tag}")

      else:
        core.scr.warning(f"App: {name} not found. Installing...")
        await install_app(core, url, name, tag)
        core.scr.success(f"App Installed: ({name}) {tag}")

    except Exception as e:
      action = "Updating" if is_installed else "Installing"
      core.scr.error(f"Error {action} App ({name}): {e}")

      if required:
        core.scr.info("Quitting...")
        raise SystemExit


# ---------------------- Setup
async def setup_apps(core) -> None:
  await pre_check_apps(core)