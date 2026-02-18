from os import environ
from pathlib import Path


class KikxPaths:
  def _get_env(self, name):
    value = environ.get(name, None)
    if value is None:
      raise KeyError(f"Value not found: {name}")
    
    return Path(value).resolve()

  @property
  def data(self):
    return self._get_env("KIKX_APP_DATA_PATH")

  @property
  def storage(self):
    return self._get_env("KIKX_STORAGE_PATH")
  
  @property
  def app(self):
    return self._get_env("KIKX_APP_PATH")

  @property
  def home(self):
    return self._get_env("KIKX_HOME_PATH")
  


  
