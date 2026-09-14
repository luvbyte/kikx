class KikxGConfig:
  def __init__(self) -> None:
    self.dev_mode: bool = True


# ---------------------- Global Config
class GlobalConfig:
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance.kikx = KikxGConfig()

    return cls._instance