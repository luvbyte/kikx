from os import environ
from pathlib import Path
from nekolib import panel, js
from nekolib.process import sh



script_path = Path(environ.get("KIKX_HOME_PATH")) / "love"
sh(f"{script_path}").pipe()


