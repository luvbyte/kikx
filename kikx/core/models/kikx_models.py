from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional

# -------------------------------------
# Configuration Models
# -------------------------------------
class ServerModel(BaseModel):
  host: str = Field("127.0.0.1", description="Host to bind the server")
  port: int = Field(8000, ge=1000, le=65535, description="Port to bind the server")
  #reload: bool = Field(True, description="Enable automatic reloading")
  log_level: Literal["critical", "error", "warning", "info", "debug"] = Field("critical", description="Logging level")

class PluginModel(BaseModel):
  path: str = Field(..., description="plugin path")

class ServiceModel(BaseModel):
  title: str = Field(..., description="service title")
  # path: str = Field(..., description="service path")
  main: str = Field("srv", description="Service module relative path")
  type: Literal["k1", "k2"] = Field("k1", description="Service module Type")
  # system: bool = Field(False, description="Checks every route if secure and will apply")

class ServicesModel(BaseModel):
  installed: Dict[str, ServiceModel] = Field({}, description="Service")
  enabled: List[str] = Field([], description="Enabled services")

class UIConfigModel(BaseModel):
  path: str = Field(..., description="Ui path")

class ConfigSettingsModel(BaseModel):
  pass

# config/kikx.json
class RootConfigModel(BaseModel):
  settings: ConfigSettingsModel = Field(
    default_factory=ConfigSettingsModel,
    description="Settings of j4k"
  )
  server: ServerModel = Field(default_factory=ServerModel, description="Server config")
  plugins: Dict[str, PluginModel] = Field({}, description="Plugins")

  ui: Dict[str, UIConfigModel] = Field({}, description="UIs")

