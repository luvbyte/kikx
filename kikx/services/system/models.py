from typing import Literal, Optional, Dict, Union, List
from pydantic import BaseModel



class NotifyModel(BaseModel):
  type: Literal['info', 'error'] = "info"
  msg: str
  delay: int = 0
  extra: dict = {}
  displayEvenActive: bool = False

class AlertModel(BaseModel):
  type: Literal['info', 'warning', 'success', 'error'] = "info"
  msg: Union[str, List[str]]
  delay: int = 0
  extra: dict = {}
  priority: Literal['less', 'high', 'normal'] = 'normal'

class UserSettingsModel(BaseModel):
  settings: dict

class ClientAppEventModel(BaseModel):
  app_id: str
  event: str
  payload: dict = {}
