from typing import Literal

from pydantic import Field, field_validator

from .app import KIKX_SERVICE
from .base import StrictBaseModel


# ---------------------- Server
class ServerModel(StrictBaseModel):
  host: str = Field(
    "127.0.0.1",
    description="Host to bind the server",
  )

  port: int = Field(
    1303,
    ge=1000,
    le=65535,
    description="Port to bind the server",
  )

  log_level: Literal[
    "critical",
    "error",
    "warning",
    "info",
    "debug",
  ] = Field(
    "error",
    description="Logging level",
  )

  access_log: bool = Field(
    False,
    description="Server access logs",
  )

  timeout: int = Field(
    3,
    ge=3,
    le=20,
    description="Graceful shutdown time",
  )


# ---------------------- Services
class ServicesConfigModel(StrictBaseModel):
  disabled: list[KIKX_SERVICE] = Field(default_factory=list)

  @field_validator("disabled")
  @classmethod
  def deduplicate(cls, value: list[KIKX_SERVICE]) -> list[KIKX_SERVICE]:
    return list(dict.fromkeys(value))


# ---------------------- User
class UserDataModel(StrictBaseModel):
  name: str = Field(
    "kikx",
    min_length=1,
    max_length=256,
    description="Name",
  )


# ---------------------- Auth
class AuthModel(StrictBaseModel):
  access: str = Field(
    "kikx",
    min_length=1,
    max_length=256,
    description="Access key",
  )

  ui: str = Field(
    "mui",
    description="Default UI",
  )


# ---------------------- Config
class KikxConfigModel(StrictBaseModel):
  server: ServerModel = Field(
    default_factory=ServerModel,
    description="Server config",
  )

  auth: AuthModel = Field(
    default_factory=AuthModel,
    description="Auth config",
  )

  user: UserDataModel = Field(
    default_factory=UserDataModel,
    description="User data",
  )

  services: ServicesConfigModel = Field(
    default_factory=ServicesConfigModel,
    description="Services config",
  )


# ---------------------- Schema
SCHEMA = {
  "auth": {
    "type": "section",
    "label": "Authentication",
    "description": "Authentication configuration",
    "fields": {
      "access": {
        "type": "text",
        "label": "Access Key",
        "description": "Access key",
        "required": True,
        "minLength": 1,
        "maxLength": 256,
      },
      "ui": {
        "type": "text",
        "label": "Default UI",
        "description": "Default UI",
        "required": True,
      },
    },
  },

  "user": {
    "type": "section",
    "label": "User",
    "description": "User data",
    "fields": {
      "name": {
        "type": "text",
        "label": "Name",
        "description": "Name",
        "required": True,
        "minLength": 1,
        "maxLength": 256,
      },
    },
  },

  "server": {
    "type": "section",
    "label": "Server (req. Restart)",
    "description": "Server configuration",
    "fields": {
      "host": {
        "type": "text",
        "label": "Host",
        "description": "Host to bind the server",
        "required": True,
      },
      "port": {
        "type": "number",
        "label": "Port",
        "description": "Port to bind the server",
        "required": True,
        "min": 1000,
        "max": 65535,
        "step": 1,
      },
      "log_level": {
        "type": "select",
        "label": "Log Level",
        "description": "Logging level",
        "options": [
          {"label": "Critical", "value": "critical"},
          {"label": "Error", "value": "error"},
          {"label": "Warning", "value": "warning"},
          {"label": "Info", "value": "info"},
          {"label": "Debug", "value": "debug"},
        ],
      },
      "access_log": {
        "type": "checkbox",
        "label": "Access Log",
        "description": "Server access logs",
      },
      "timeout": {
        "type": "number",
        "label": "Timeout",
        "description": "Graceful shutdown time",
        "default": 3,
        "min": 3,
        "max": 20,
        "step": 1,
      },
    },
  },
}