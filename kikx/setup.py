# Setup kikx fs
import shutil

from pathlib import Path

from core.console import Console
from core.setup.fs import SetupFS
from core.__about__ import __version__

from config.setup import VOLUMES_PATH, KIKX_CONFIG


scr = Console()


# ---------------------- Config

def ask_option():
  scr.warning("Storage path already exists...")

  while True:
    option = scr.ask("Select [ (C)ontinue/(O)verride/(Q)uit ] ").strip().lower()

    if option in {"c", "o", "q"}:
      return option

    scr.error("Invalid option. Please select (c/o/q).")


def ask_storage_path():
  while True:
    fs_name = scr.ask("Enter storage name", "kikxfs").strip()

    try:
      path = Path(VOLUMES_PATH / fs_name).expanduser()
    except (TypeError, ValueError):
      scr.error("Invalid storage path.")
      continue

    # Avoid accidentally using the filesystem root.
    if path == path.anchor:
      scr.error("Using the filesystem root as storage is not allowed.")
      continue

    return path


def remove_existing_path(fs_path):
  if fs_path.is_dir() and not fs_path.is_symlink():
    shutil.rmtree(fs_path)
  else:
    fs_path.unlink()


# ---------------------- Main

def main():
  scr.print_banner()
  scr.title(f"KIKX SETUP v{__version__}")

  fs_path = ask_storage_path()

  if fs_path.exists():
    option = ask_option()

    if option == "q":
      scr.print("Setup cancelled.")
      return

    if option == "o":
      try:
        remove_existing_path(fs_path)
      except OSError as e:
        scr.error(f"Unable to remove storage path: {e}")
        return

  try:
    setup = SetupFS(fs_path)
    setup.pre_create()
  except OSError as e:
    scr.error(f"Unable to initialize storage: {e}")
    return

  access_key = scr.ask("Set access key", "kikx").strip()
  username = scr.ask("Set username", "kikx").strip()
  setup.setup_config({
    **KIKX_CONFIG,
    "auth": { "access": access_key },
    "user": { "name": username }
  })

  scr.title("SETUP COMPLETE")


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    scr.print("\nSetup cancelled.")
  except Exception as e:
    scr.error(e)