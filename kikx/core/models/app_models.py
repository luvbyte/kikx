from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, field_serializer

from core.func.func import FuncXModel



# App iframs flags
IframeSandboxFlag = Literal[
  "allow-scripts",
  "allow-same-origin",  # 

  "allow-forms",
  "allow-top-navigation",
  "allow-top-navigation-by-user-activation",
  "allow-top-navigation-to-custom-protocols",

  "allow-popups",
  "allow-popups-to-escape-sandbox",

  "allow-downloads",
  "allow-downloads-without-user-activation",

  "allow-modals",
  "allow-pointer-lock",
  "allow-orientation-lock",
  "allow-presentation",

  "allow-storage-access-by-user-activation",
]

# App iframs allow features
IframeAllowFeature = Literal[
  "accelerometer",
  "ambient-light-sensor",
  "autoplay",
  "battery",
  "camera",
  "clipboard-read",
  "clipboard-write",
  "display-capture",
  "document-domain",
  "encrypted-media",
  "execution-while-not-rendered",
  "execution-while-out-of-viewport",
  "fullscreen",
  "gamepad",
  "geolocation",
  "gyroscope",
  "hid",
  "identity-credentials-get",
  "idle-detection",
  "interest-cohort",
  "keyboard-map",
  "magnetometer",
  "microphone",
  "midi",
  "navigation-override",
  "payment",
  "picture-in-picture",
  "publickey-credentials-get",
  "screen-wake-lock",
  "serial",
  "speaker-selection",
  "storage-access",
  "usb",
  "web-share",
  "xr-spatial-tracking",
]

# App dynamic modules
APP_MODULE = Literal['tasks']

# App tasks module model
class AppModuleTasksConfigModel(BaseModel):
  shell: bool = False
  # KIKX_ env variables
  kikx_env: bool = True
  # If this is False then uses program env
  sandbox: bool = False
  # env variables in key/values
  env: Dict[str, str] = {}
  # Main program to run while running tasks
  main: str = Field('python3 -u {app_path}/tasks/{name}.py {args}', description="Prefix for all tasks")

# App storage access permissions
class AppStoragePermissionsModel(BaseModel):
  app: Optional[Literal['read']] = Field(None, description="App storage permission")
  root: Optional[Literal['read', 'write', '*']] = Field(None, description="Root storage permission")
 
  home: Optional[Literal['read', 'write', '*']] = Field(None, description="Home storage permission")

  def check_read(self, storage: str) -> bool:
    permission = getattr(self, storage, None)
    if permission is None:
      raise ValueError(f"Invalid storage name: {storage}")
    return permission in {'read', '*'}

  def check_write(self, storage: str) -> bool:
    permission = getattr(self, storage, None)
    if permission is None:
      raise ValueError(f"Invalid storage name: {storage}")
    return permission in {'write', '*'}
  
  def check(self, storage, _type):
    func = {
      "read": self.check_read,
      "write": self.check_write
    }.get(_type)
    if func is None:
      raise ValueError(f"Invalid check type: {_type}")
    
    return func(storage)

# App system access permissions
class AppSystemPermissionsModel(BaseModel):
  access: List[Literal["funcx", "notify", "alert", "sessions", "info", "kpm"]] = []

  # Remove duplicates during validation
  @field_validator("access")
  @classmethod
  def deduplicate(cls, value):
    return list(dict.fromkeys(value))

  def check(self, permission):
    return permission in self.access

# Iframe model for ui
class AppIframeModel(BaseModel):
  allowfullscreen: bool = Field(False, description="Allow fullscreen mode")

  sandbox: List[IframeSandboxFlag] = []
  allow: List[IframeAllowFeature] = []

  loading: Literal["lazy", "eager"] = Field("eager", description="Lazy or eager loading")

  referrerpolicy: Literal["no-referrer", "origin", "unsafe-url"] = Field(
    "no-referrer", description="Controls referrer information"
  )

  # Remove duplicates during validation
  @field_validator("sandbox", "allow")
  @classmethod
  def deduplicate(cls, value):
    return list(dict.fromkeys(value))

  def get_dict(self):
    return {
      "allowfullscreen": self.allowfullscreen,
      "sandbox": " ".join(self.sandbox),
      "allow": "; ".join(self.allow),
      "loading": self.loading,
      "referrerpolicy": self.referrerpolicy,
    }

# APP config model in data/data/app
class AppModel(BaseModel):
  # github.luvbyte.appstore
  name: str = Field(..., description="App name")
  title: str = Field(..., description="App title")
  version: str = Field(..., description="App Version")

  kikx_version: str = Field(..., description="Minimum kikx version")

  # Frontend permissions
  iframe: AppIframeModel = Field(default_factory=AppIframeModel, description="Iframe permissons")

  # App modules to use
  modules: Dict[APP_MODULE, Dict] = Field({}, description="App modules to use")

  # Service permissions
  proxy: bool = False
  system: AppSystemPermissionsModel = Field(default_factory=AppSystemPermissionsModel, description="system permissions")
  storage: AppStoragePermissionsModel = Field(default_factory=AppStoragePermissionsModel, description="storage permissions")

  # Super permissions ( Dangerous )
  sudo: bool = False  # Access sudo

# Github source model for apps
class GithubSourceModel(BaseModel):
  url: str
  owner: str
  repo: str
  tag: Optional[str]

# App manifest app.json in app root fs
class AppManifestModel(AppModel):
  icon: str = "icon.png"
  category: str | None = None
  author: Optional[str] = Field(None, description="App Author")
  description: Optional[str] = Field(None, description="App Description")
  
  source: Union[Literal['local'], GithubSourceModel] = "local"

  # theme
  theme: str = "dark"
