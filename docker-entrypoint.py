import os
import sys
import pwd
import grp
from pathlib import Path

from config.setup import KIKX_CONFIG, STORAGE_NAME, VOLUMES_PATH
from core.setup.fs import SetupFS


def initialize_storage() -> None:
  storage_path = (VOLUMES_PATH / STORAGE_NAME).resolve()
  config_path = storage_path / "config" / "kikx.json"

  if not config_path.exists():
    access_key = os.environ.get("KIKX_ACCESS_KEY", "").strip()
    if not access_key:
      raise RuntimeError("KIKX_ACCESS_KEY is required.")

    username = os.environ.get(
      "KIKX_USERNAME", KIKX_CONFIG["user"]["name"]
    ).strip() # type: ignore

    if not username:
      raise RuntimeError("KIKX_USERNAME cannot be empty.")

    setup = SetupFS(storage_path)
    setup.pre_create()

    config = {
      **KIKX_CONFIG,
      "auth": {
        **KIKX_CONFIG["auth"],
        "access": access_key,
      },
      "user": {
        **KIKX_CONFIG["user"],
        "name": username,
      },
    }
    setup.setup_config(config)

  # Ensure the runtime user can access the persistent data.
  uid = pwd.getpwnam("nobody").pw_uid
  gid = grp.getgrnam("nogroup").gr_gid

  for root, dirs, files in os.walk(storage_path):
    os.chown(root, uid, gid)
    for name in dirs + files:
      os.chown(os.path.join(root, name), uid, gid)


if __name__ == "__main__":
  initialize_storage()
  os.execvp(sys.argv[1], sys.argv[1:])