from nekolib import panel, js
from nekolib.process import sh

from pathlib import Path

from os import environ

js.run_code("setRawOutput()")

script_path = Path(environ.get("KIKX_HOME_PATH")) / "love"

sh(f"{script_path}").pipe()


