from core.kpm import AppInstaller
from core.utils import load_app_manifest

from .pkg import fetch_from_github, is_outdated



# name: (repo, tag, required: bool)
PRE_INSTALL_APPS = {
  # Required
  "com.kikx.appstore": (
    "https://github.com/luvbyte/kikx-appstore-app",
    "v0.0.5", True
  ),
  # Optional
  "com.kikx.sessions": (
    "https://github.com/luvbyte/kikx-sessions-app",
    "v0.1.3", False
  ),
  # Optional
  "com.kikx.explorer": (
    "https://github.com/luvbyte/kikx-explorer-app",
    "v0.1.2", False
  ),
  # Optional
  "com.kikx.florix": (
    "https://github.com/luvbyte/kikx-florix-app",
    "v0.1.4", False
  )
}

async def _apply_app(core, url, name, tag, method):
  def callback(extracted_path, source):
    getattr(AppInstaller(core, extracted_path), method)(source)

  await fetch_from_github(url, name, callback, tag=tag)

# Install App
async def install_app(core, url, name, tag):
  await _apply_app(core, url, name, tag, "install")

# Updatw App
async def update_app(core, url, name, tag):
  await _apply_app(core, url, name, tag, "update")

# Precheck App
async def pre_check_apps(core) -> None:
  installed_apps = set(core.user.get_installed_apps())

  for name, (url, tag, required) in PRE_INSTALL_APPS.items():
    is_installed = name in installed_apps

    try:
      # Update App
      if is_installed:
        manifest = load_app_manifest(core, name, raw=True)

        if not is_outdated(manifest.version, tag):
          continue

        core.scr.warning(f"App: {name} outdated. Updating...")
        await update_app(core, url, name, tag)
        core.scr.success(f"App Updated: ({name}) {manifest.version} -> {tag}")
      # Install App
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

async def setup_apps(core) -> None:
  await pre_check_apps(core)
