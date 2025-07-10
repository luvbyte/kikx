from pathlib import Path
from os import mkdir
import shlex

class Storage:
  def __init__(self, storage_path):
    self.storage_path: Path = Path(storage_path).resolve()
    
    # create directory if not exists
    if not self.storage_path.exists():
      raise Exception("Storage path not found") 

    # if path is not directory
    if not self.storage_path.is_dir():
      raise Exception("Storage path must be directory") 
  
  @property
  def path(self):
    return self._storage_path
  
  def join(self, *path):
    return self.storage_path.joinpath(*path)

