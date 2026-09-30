import os
from sys import argv

from utils import get_root_path

# ----------------------------------
# KIKX STORAGE / FILESYSTEM
# ----------------------------------
VOLUMES_PATH = os.environ.get("KIKX_VOLUMES", get_root_path().parent / "volumes")
STORAGE_NAME = os.environ.get("KIKXFS", "kikxfs")

# ----------------------------------
# KIKX DEFAULT CONFIG
# ----------------------------------
KIKX_CONFIG = {
  "server": {
    "host": "127.0.0.1",
    "port": 1303,
    "log_level": "error",
    "access_log": False,
    "timeout": 3
  },
  "auth": {
    "access": "kikx",
    "ui": "mui"
  },
  "user": {
    "name": "kikx"
  },
  "services": {
    "disabled": []
  }
}

# ----------------------------------
# PRE INSTALL APPS
# ----------------------------------
# name: (repo, tag, required: bool)
PRE_INSTALL_APPS = {
  "com.kikx.appstore": (
    "https://github.com/luvbyte/kikx-appstore-app",
    "v0.0.9", True
  ),
  "com.kikx.sessions": (
    "https://github.com/luvbyte/kikx-sessions-app",
    "v0.1.4", True
  ),
  "com.kikx.explorer": (
    "https://github.com/luvbyte/kikx-explorer-app",
    "v0.1.7", True
  ),
  "com.kikx.florix": (
    "https://github.com/luvbyte/kikx-florix-app",
    "v0.1.7", False
  )
}

# ----------------------------------
# PRE INSTALL UI
# ----------------------------------
# name: (repo, tag, required: bool)
PRE_INSTALL_UI = {
  # Default UI
  "mui": (
    "https://github.com/luvbyte/kikx-mui",
    "v0.4.3",
    True
  ),
}

# ----------------------------------
# ADMIN APPS
# ----------------------------------
ADMIN_APPS = [
  "com.kikx.appstore",
  "com.kikx.sessions",
  "com.kikx.explorer"
]

# ----------------------------------
# ADMIN UI
# ----------------------------------
ADMIN_UIS = [ "mui" ]
