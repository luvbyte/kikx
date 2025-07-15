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

# --------------------------- Users models
class AppMountPaths(BaseModel):
  home: str = Field(..., description="Home path")
  file: str = Field(..., description="App path")
  data: str = Field(..., description="App data path")

# permissions: {}
class AppIframeModel(BaseModel):
  allowfullscreen: bool = Field(False, description="Allow fullscreen mode")

  sandbox: str = Field("", description="Security restrictions for iframe")
  allow: str = Field("", description="Permissions for camera, microphone, etc.")

  loading: Literal["lazy", "eager"] = Field("eager", description="Lazy or eager loading")
  
  referrerpolicy: Literal["no-referrer", "origin", "unsafe-url"] = Field(
    "no-referrer", description="Controls referrer information"
  )
  # maybe remove in future
  style: str = Field("border: none;", description="CSS styles for iframe")
  
# app: {}
class AppModel(BaseModel):
  # permissions: {}
  # find why i need title 
  title: str = Field(..., description="App title")
  iframe: AppIframeModel = Field(..., description="Iframe permissons")
  modules: list = Field([], description="App modules to use")

  storage: List[str] = Field([], description="storage permissions")
  #url: str = Field(..., description="Url of app")
  # task template
  #task_template: str = Field("venv/bin/python3 -u taskwrap.py", description="Prefix for all tasks")
  #task_template: str = Field('$KIKX_STORAGE_PATH/venv/bin/python3 -u $KIKX_APP_PATH/tasks/{name}.py {args}', description="Prefix for all tasks")
  task_template: str = Field('$PY_PATH -u $KIKX_APP_PATH/tasks/{name}.py {args}', description="Prefix for all tasks")
  # implement in all services
  services: list = Field([], description="Services that can be used by app")

# deprecated
class AppsModel(BaseModel):
  installed: Dict[str, AppModel] = Field({}, description="Installed Apps")
  disabled: List[str] = Field([], description="Disabled apps")

# remove in future
class UserSettingsModel(BaseModel):
  silent: bool = Field(False, description="Silent mode")

class UserDataModel(BaseModel):
  name: str = Field(..., description="User full name")
  age: int = Field(..., description="User age")
  gender: Literal['male', 'female'] = Field(..., description="User gender")

class UserModel(BaseModel):
  name: str = Field(..., description="User name")
  username: str = Field(..., description="Username")
  password: str = Field(..., description="Password")
  
  ui: List[str] = Field(..., description="Ui list")
  default_ui: str = Field(..., description="default one to use")

# --------------------------- kikx models
# settings : {} kikx settings


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
  require_auth: bool = Field(True, description="Require auth")


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

