from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------- Types
EXTRATYPES = str | int | float | bool | list[str]


# ---------------------- Alert
class AlertModel(BaseModel):
  message: str

  uid: str | None = None
  type: Literal["info", "warning", "success", "error"] = "info"
  label: str | None = None
  extra: dict[str, EXTRATYPES] = Field(default_factory=dict)
  priority: Literal["less", "high", "normal"] = "normal"
  sticky: bool = False
  silent: bool = False


# ---------------------- User Settings
class UserSettingsModel(BaseModel):
  settings: dict


# ---------------------- Client App Event
class ClientAppEventModel(BaseModel):
  app_id: str
  event: str
  payload: Any


# ---------------------- Invoke
class InvokeModel(BaseModel):
  action: str
  payload: dict[str, Any]
  res_id: str | None = None