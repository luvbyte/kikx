# global singleton config file
class GlobalConfig:
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance.data = {}  # Shared global data
    return cls._instance


global_config = GlobalConfig()
