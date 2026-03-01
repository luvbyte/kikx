import shutil
from pathlib import Path

# Auto setup and config kikxfs
# On hold
class SetupFS:
  def __init__(self, base: str | Path):
    self.base = Path(base).resolve()

  @property
  def is_exists(self):
    return self.base.exists()

  def precheck(self, is_reset=False):
    # if path exists
    if self.is_exists and not is_reset:
      raise Exception(f"{self.base} already exists.")

  def setup(self, is_reset=False):
    self.precheck(is_reset=is_reset)

    if self.is_exists and is_reset:
      shutil.rmtree(self.base)

    self.base.mkdir(parents=True, exist_ok=True)

  def postcheck(self):
    if not self.base.exists():
      raise Exception(f"{self.base} was not created properly.")
    return True


class SetupUser:
  def __init__(self, fs: SetupFS):
    self.fs = fs

  def setup(self):
    user_dir = self.fs.base / "data/config"
    user_dir.mkdir(exist_ok=True)


class SetupUI:
  def __init__(self, fs: SetupFS):
    self.fs = fs

  def setup(self):
    ui_dir = self.fs.base / "ui"
    ui_dir.mkdir(exist_ok=True)


class SetupApps:
  def __init__(self, fs: SetupFS):
    self.fs = fs

  def setup(self):
    apps_dir = self.fs.base / "apps"
    apps_dir.mkdir(exist_ok=True)


class SetupPlugins:
  def __init__(self, fs: SetupFS):
    self.fs = fs

  def setup(self):
    plugins_dir = self.fs.base / "plugins"
    plugins_dir.mkdir(exist_ok=True)


class ScanFS:
  def __init__(self, fs: SetupFS):
    self.fs = fs

  def scan(self):
    if not self.fs.is_exists:
      raise Exception("Filesystem not initialized.")

    return [p.name for p in self.fs.base.iterdir()]



