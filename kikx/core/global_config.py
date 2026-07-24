from os import environ
from pathlib import Path

class KikxGConfig:
  def __init__(self) -> None:
    self.dev_mode: bool = True
    self._fallack_fs_path: str = "../kikxfs"

  def get_fs_path(self) -> Path:
    return Path(environ.get("KIKXFS", self._fallack_fs_path))

# global singleton config file
class GlobalConfig:
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance.kikx = KikxGConfig()  # Shared global object
    return cls._instance

