import json


from core.errors import raise_error, Error
from core.storage import Storage

from .models import RootConfigModel
from lib.parser import parse_config
from lib import utils

from pathlib import Path
from utils import get_root_path

from lib.utils import ensure_dir

#def ensure_dir(path):
#  """Ensure the directory exists. If not, create it."""
#  Path(path).mkdir(parents=True, exist_ok=True)
#  return path

# ----------- config apis
# config api 
class Config:
  def __init__(self, storage):
    self._storage = Storage(storage)
    self._kikx = parse_config(self.resolve_path("storage://config/kikx.json"), RootConfigModel)

  @property
  def storage(self):
    return self._storage
  
  # kikx config deprecated
  @property
  def kikx(self):
    return self._kikx

  # ----------- get_apps_list in apps_path
  def get_apps_list(self):
    # List only folders (directories) efficiently
    return list(self.apps_path.glob("*/"))  # Uses glob for better performance

  # returns Path
  def resolve_path(self, line: str):
    # return utils.resolve_path(line)
    splitted = line.split("://", 1)
    if len(splitted) <= 1:
      return line # raw path

    protocol, path = splitted
    if protocol == "storage":
      return self.storage.join(path)
    elif protocol == "share":
      return self.storage.join("share", path)
    elif protocol == "apps":
      return self.storage.join("apps", path)
    elif protocol == "data":
      return self.storage.join("data", path)
    elif protocol == "home":
      return self.storage.join("home", path)
    elif protocol == "kikx":
      return self.storage.join(get_root_path(), path)
    
    return line
  
  @property
  def share_path(self):
    return ensure_dir(self.resolve_path("storage://share"))
  
  # home/share path
  @property
  def files_path(self):
    return ensure_dir(self.resolve_path("home://share"))

  @property
  def apps_path(self):
    return ensure_dir(self.resolve_path("apps://"))
