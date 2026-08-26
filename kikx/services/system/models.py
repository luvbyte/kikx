from typing import Literal, Any
from pydantic import BaseModel, Field


class AlertModel(BaseModel):
  uid: str | None = None
  type: Literal['info', 'warning', 'success', 'error'] = "info"
  message: str
  extra: dict = Field(default_factory=dict)
  priority: Literal['less', 'high', 'normal'] = 'normal'
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
