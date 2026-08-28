from typing import Literal, Any
from pydantic import BaseModel, Field

EXTRATYPES = str | int | float | bool | list[str]

class AlertModel(BaseModel):
  message: str

  uid: str | None = None
  type: Literal['info', 'warning', 'success', 'error'] = "info"
  label: str | None = None
  extra: dict[str, EXTRATYPES] = Field(default_factory=dict)
  priority: Literal['less', 'high', 'normal'] = 'normal'
  sticky: bool = False
  silent: bool = False

class UserSettingsModel(BaseModel):
  settings: dict

class ClientAppEventModel(BaseModel):
  app_id: str
  event: str
  payload: Any

class InvokeModel(BaseModel):
  action: str
  payload: dict[str, Any]
