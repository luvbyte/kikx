import os
import platform
import shutil

from pathlib import Path

from lib.os import get_username


class OS:
  def __init__(self):
    self.name = os.name
    self.system = platform.system()
    self.release = platform.release()
    self.version = platform.version()
    self.machine = platform.machine()
    self.processor = platform.processor()
    self.architecture = platform.architecture()[0]

  # ---------------------- System information

  @property
  def info(self) -> dict:
    return {
      "name": self.name,
      "system": self.system,
      "release": self.release,
      "version": self.version,
      "machine": self.machine,
      "processor": self.processor,
      "architecture": self.architecture,
    }

  @property
  def is_windows(self):
    return self.system == "Windows"

  @property
  def is_linux(self):
    return self.system == "Linux"

  @property
  def is_macos(self):
    return self.system == "Darwin"

  @property
  def cpu_count(self):
    return os.cpu_count()

  @property
  def username(self):
    return get_username()

  @property
  def home(self):
    return Path.home()

  @property
  def cwd(self):
    return Path.cwd()

  # ---------------------- Environment variables

  def getenv(self, key, default=None):
    return os.getenv(key, default)

  def setenv(self, key, value):
    os.environ[key] = str(value)

  def unsetenv(self, key):
    return os.environ.pop(key, None)

  @property
  def environment(self):
    return dict(os.environ)

  # ---------------------- Commands

  def which(self, program):
    return shutil.which(program)

  def __repr__(self):
    return (
      f"OS(system={self.system!r}, "
      f"release={self.release!r}, "
      f"architecture={self.architecture!r})"
    )