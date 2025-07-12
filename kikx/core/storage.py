from pathlib import Path
from os import mkdir
import shlex

from lib.utils import ensure_dir


class Storage:
  def __init__(self, storage_path):
    self.storage_path: Path = ensure_dir(Path(storage_path).resolve())

    # if path is not directory
    if not self.storage_path.is_dir():
      raise Exception("Storage path must be directory")
    
    # works for now
    precreate = ["home", "apps", "share", "data", "data/app", "data/data", "bin", "root"]
    for name in precreate:
      ensure_dir(self.storage_path / name)

  @property
  def path(self):
    return self._storage_path
  
  def join(self, *path):
    return self.storage_path.joinpath(*path)

