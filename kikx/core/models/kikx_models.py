from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator



# Optional Services
DISABLE_SERVICES = Literal['proxy', 'fs', 'expose', 'kvx']


# Server config model
class ServerModel(BaseModel):
  host: str = Field("127.0.0.1", description="Host to bind the server")
  port: int = Field(1303, ge=1000, le=65535, description="Port to bind the server")
  log_level: Literal["critical", "error", "warning", "info", "debug"] = Field("critical", description="Logging level")

# Services config model 
class ServicesConfigModel(BaseModel):
  disabled: List[DISABLE_SERVICES] = []

  # Remove duplicates during validation
  @field_validator("disabled")
  @classmethod
  def deduplicate(cls, value):
    return list(dict.fromkeys(value))

# UI config 
class UIConfigModel(BaseModel):
  path: str = Field(..., description="Ui path")

# ...
class ConfigSettingsModel(BaseModel):
  pass

# main kikx config in config/kikx.json
class RootConfigModel(BaseModel):
  settings: ConfigSettingsModel = Field(default_factory=ConfigSettingsModel, description="Settings of kikx")
  server: ServerModel = Field(default_factory=ServerModel, description="Server config")

  ui: Dict[str, UIConfigModel] = Field({}, description="UIs")

