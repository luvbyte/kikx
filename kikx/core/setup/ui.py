import shutil

from lib.utils import joinpath
from core.kpm import UIInstaller

from .pkg import fetch_from_github, is_outdated



# name: (repo, tag, required: bool)
PRE_INSTALL_UI = {
  # MUI
  "mui": (
    "https://github.com/luvbyte/kikx-mui",
    "v0.3.2",
    True
  ),
}

# Install UI
async def install_ui(core, url, name, tag):
  # Install
  def install(extracted_path, source):
    UIInstaller(core, name, extracted_path).install(force=True)

  await fetch_from_github(url, name, install, tag=tag)

def get_ui_version(core, name) -> str:
  return core.user.load_ui_config(name).version

# Precheck UI
async def pre_check_ui(core) -> None:
  installed = set(core.auth.user_config.ui)

  for name, (url, tag, required) in PRE_INSTALL_UI.items():
    is_installed = name in installed

    try:
      if is_installed:
        version = get_ui_version(core, name)

        if not is_outdated(version, tag):
          continue

        core.scr.warning(f"UI: {name} outdated. Updating...")
        
        action = "Updated"
      else:
        core.scr.warning(f"UI: {name} not found. Installing...")

        version = None
        action = "Installed"

      await install_ui(core, url, name, tag)

      if version:
        core.scr.success(f"UI {action}: ({name}) {version} -> {tag}")
      else:
        core.scr.success(f"UI {action}: ({name}) {tag}")
    except Exception as e:
      operation = "Updating" if is_installed else "Installing"
      core.scr.error(f"Error {operation} UI ({name}): {e}")

      if required:
        core.scr.info("Quitting...")
        raise SystemExit

async def setup_ui(core) -> None:
  await pre_check_ui(core)
