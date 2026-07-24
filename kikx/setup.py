# Setup kikx fs
import shutil
from core.console import Console
from pathlib import Path
from core.setup.fs import SetupFS

from core.__about__ import __version__


scr = Console()

# ----------------- config
def start_setup(setup):
  name = scr.ask("Enter name: ")
  username = scr.ask("Enter username: ")
  access = scr.ask("Access Key: ")

  setup.setup_config({
    "kikx": {
      "settings": {}
    },
    "auth": {
      "access": access,
      "ui": [],
      "default_ui": ""
    },
    "services": {
      "disabled": []
    },
    "user_data": {
      "name": name,
      "username": username
    }
  })

  scr.title("SETUP COMPLETE")

def ask_option():
  scr.warning("Storage path already exists...")
  while True:
    option = scr.ask("Select [ (C)ontinue/(O)verride/(Q)uit ] ").strip().lower()
    if option in ["c", "o", "q"]:
      return option
    
    scr.print("Please select (c/o/q).")

def main():
  scr.print_banner()
  scr.title("KIKX SETUP")

  fs_path = Path(scr.ask("Enter storage path", "../kikxfs"))

  if fs_path.exists():
    option = ask_option()

    if option == "q":
      return
    if option == "o":
      shutil.rmtree(fs_path)

  setup = SetupFS(fs_path)
  setup.pre_create()
  start_setup(setup)

if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    scr.error(e)
  except KeyboardInterrupt:
    pass
