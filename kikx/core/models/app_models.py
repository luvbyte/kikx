# core router models
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

from core.func.func import FuncXModel

# models used for app opening routes
# /open-app
class CloseAppModel(BaseModel):
  app_id: str
  client_id: str
# /close-app
class OpenAppModel(BaseModel):
  name: str
  client_id: str
  
class AppsListModel(BaseModel):
  client_id: str

# ---------+++--------
class AppStoragePermissionsModel(BaseModel):
  app: Optional[Literal['r', 'w', '*']] = Field(None, description="App storage permission")
  root: Optional[Literal['r', 'w', '*']] = Field(None, description="Root storage permission")
 
  home: Optional[Literal['r', 'w', '*']] = Field(None, description="Home storage permission")

  def check_read(self, storage: str) -> bool:
    permission = getattr(self, storage, None)
    if permission is None:
      raise ValueError(f"Invalid storage name: {storage}")
    return permission in {'r', '*'}

  def check_write(self, storage: str) -> bool:
    permission = getattr(self, storage, None)
    if permission is None:
      raise ValueError(f"Invalid storage name: {storage}")
    return permission in {'w', '*'}
  
  def check(self, storage, _type):
    func = {
      "read": self.check_read,
      "write": self.check_write
    }.get(_type)
    if func is None:
      raise ValueError(f"Invalid check type: {_type}")
    
    return func(storage)

class AppSystemPermissionsModel(BaseModel):
  nav: Literal['pass', 'stop'] = Field("pass", description="Catch navigation")

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
  # find why i need title 
  title: str = Field(..., description="App title")
  iframe: AppIframeModel = Field(..., description="Iframe permissons")
  modules: List[str] = Field([], description="App modules to use")

  system: AppSystemPermissionsModel = Field(default_factory=AppSystemPermissionsModel, description="System permissions")
  storage: AppStoragePermissionsModel = Field(default_factory=AppStoragePermissionsModel, description="storage permissions")
  
  task_template: str = Field('python3 -u $KIKX_APP_PATH/tasks/{name}.py {args}', description="Prefix for all tasks")
  # implement in all services
  services: List[str] = Field([], description="Services that can be used by app")
