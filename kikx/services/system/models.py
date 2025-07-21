from typing import Literal, Optional, Dict
from pydantic import BaseModel



class NotifyModel(BaseModel):
  type: Literal['info', 'error'] = "info"
  msg: str
  delay: int = 0
  extra: dict = {}
  displayEvenActive: bool = False

class UserSettingsModel(BaseModel):
  settings: dict
