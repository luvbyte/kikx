from typing import Literal, Any
from pydantic import BaseModel, Field, field_validator, field_serializer

from core.func.func import FuncXModel
from .base import GithubSourceModel

StorageName = Literal["root", "home", "os", "osr"]
PermissionType = Literal["read", "write"]

# App iframe sandbox flags
IframeSandboxFlag = Literal[
  "allow-scripts",  # Allows JavaScript execution inside the iframe.
  "allow-same-origin",  # Uses the iframe's real origin instead of a unique sandbox origin (enables cookies, localStorage, IndexedDB, etc.).

  "allow-forms",  # Allows HTML form submission.
  "allow-top-navigation",  # Allows the iframe to navigate the top-level page.
  "allow-top-navigation-by-user-activation",  # Allows top-level navigation only after a user gesture.
  "allow-top-navigation-to-custom-protocols",  # Allows navigation to custom URI schemes (e.g. mailto:, tel:, myapp:).

  "allow-popups",  # Allows opening new windows/tabs via window.open() or target="_blank".
  "allow-popups-to-escape-sandbox",  # Popups are opened without inheriting the iframe's sandbox restrictions.

  "allow-downloads",  # Allows file downloads.
  "allow-downloads-without-user-activation",  # Allows downloads without requiring a user gesture.

  "allow-modals",  # Allows alert(), confirm(), and prompt() dialogs.
  "allow-pointer-lock",  # Allows use of the Pointer Lock API (mouse capture).
  "allow-orientation-lock",  # Allows locking the screen orientation.
  "allow-presentation",  # Allows use of the Presentation API (external displays).

  "allow-storage-access-by-user-activation",  # Allows Storage Access API after a user gesture (third-party storage access).
]

# App iframe Permissions Policy ("allow" attribute) features
IframeAllowFeature = Literal[
  "accelerometer",  # Access the device accelerometer.
  "ambient-light-sensor",  # Access the ambient light sensor.
  "autoplay",  # Allow media to autoplay.
  "battery",  # Access the Battery Status API (mostly deprecated).
  "camera",  # Access the user's camera.
  "clipboard-read",  # Read from the system clipboard.
  "clipboard-write",  # Write to the system clipboard.
  "display-capture",  # Capture the screen, window, or tab.
  "document-domain",  # Allow use of document.domain for legacy same-origin relaxation.
  "encrypted-media",  # Play DRM-protected media (EME).
  "execution-while-not-rendered",  # Continue executing while the iframe is not rendered.
  "execution-while-out-of-viewport",  # Continue executing while the iframe is off-screen.
  "fullscreen",  # Allow entering fullscreen mode.
  "gamepad",  # Access connected game controllers.
  "geolocation",  # Access the user's location.
  "gyroscope",  # Access the device gyroscope.
  "hid",  # Access Human Interface Devices (HID).
  "identity-credentials-get",  # Allow Identity Credentials / FedCM API.
  "idle-detection",  # Detect whether the user or device is idle.
  "interest-cohort",  # Legacy FLoC permission (obsolete in modern browsers).
  "keyboard-map",  # Access the Keyboard Layout Map API.
  "magnetometer",  # Access the device magnetometer.
  "microphone",  # Access the user's microphone.
  "midi",  # Access MIDI devices.
  "navigation-override",  # Allow overriding certain browser navigation behaviors.
  "payment",  # Allow use of the Payment Request API.
  "picture-in-picture",  # Allow Picture-in-Picture video mode.
  "publickey-credentials-get",  # Allow WebAuthn (passkeys/security keys).
  "screen-wake-lock",  # Prevent the screen from sleeping.
  "serial",  # Access serial devices.
  "speaker-selection",  # Allow selecting audio output devices.
  "storage-access",  # Allow the Storage Access API.
  "usb",  # Access USB devices through WebUSB.
  "web-share",  # Allow use of the Web Share API.
  "xr-spatial-tracking",  # Access WebXR devices and spatial tracking (AR/VR).
]

# System Access List 
ACCESS_LIST = Literal[
  "funcx", # Run funcx functions from js
  "alert", # Alert notifications
  "sessions", # Client(UI) sessions managing
  "kpm", # Install / Uninstall Apps
  "invoke" # Invoke actions
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
  # Custum env dict
  env: dict[str, str] = Field(default_factory=dict)
  # Main program to run while running tasks
  main: str = Field('python3 -u {app_path}/tasks/{name}.py {args}', description="Prefix for all tasks")

# App storage access permissions
class AppStoragePermissionsModel(BaseModel):
  root: Literal["read", "write", "*"] | None = Field(
    default=None,
    description="Root storage permission",
  )

  os: Literal["read", "write", "*"] | None = Field(
    default=None,
    description="OS home storage permission",
  )

  osr: Literal["read", "write", "*"] | None = Field(
    default=None,
    description="OS root storage permission",
  )

  home: Literal["read", "write", "*"] | None = Field(
    default=None,
    description="Home storage permission",
  )

  def _get_permission(self, storage: StorageName) -> str | None:
    if storage not in self.__class__.model_fields:
      raise ValueError(f"Invalid storage name: {storage}")

    return getattr(self, storage)

  def check_read(self, storage: StorageName) -> bool:
    permission = self._get_permission(storage)
    return permission in {"read", "*"}

  def check_write(self, storage: StorageName) -> bool:
    permission = self._get_permission(storage)
    return permission in {"write", "*"}

  def check(
    self,
    storage: StorageName,
    permission_type: PermissionType,
  ) -> bool:
    permission = self._get_permission(storage)

    if permission_type == "read":
      return permission in {"read", "*"}

    return permission in {"write", "*"}

# App system access permissions
class AppSystemPermissionsModel(BaseModel):
  access: list[ACCESS_LIST] = Field(default_factory=list)

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

  sandbox: list[IframeSandboxFlag] = Field(default_factory=list)
  allow: list[IframeAllowFeature] = Field(default_factory=list)

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
  # org.author.name
  name: str = Field(
    ...,
    min_length=1,
    max_length=20,
    description="App name",
  )
  title: str = Field(
    ...,
    min_length=1,
    max_length=20,
    description="App title",
  )
  version: str = Field(
    ...,
    pattern=r"^\d+\.\d+\.\d+$",
    description="App version (major.minor.patch)",
  )
  kikx_version: str = Field(
    ...,
    pattern=r"^(?:(?:\^|~|~=|>=|<=|==|!=|>|<)?\d+\.\d+\.\d+)(?:,(?:(?:>=|<=|==|!=|>|<)\d+\.\d+\.\d+))*$",
    description="Required Kikx version",
  )

  # Frontend permissions
  iframe: AppIframeModel = Field(default_factory=AppIframeModel, description="Iframe permissons")

  # App modules to use
  modules: dict[APP_MODULE, dict[str, Any]] = Field(default_factory=dict, description="App modules to use")

  # Service permissions
  os: bool = False
  kv: bool = False
  proxy: bool = False
  micro: bool = False
  tasker: bool = False

  # Track ws messages if ws disconnected
  ws_tracking: bool = True

  # System and Storage permissions
  system: AppSystemPermissionsModel = Field(default_factory=AppSystemPermissionsModel, description="System permissions")
  storage: AppStoragePermissionsModel = Field(default_factory=AppStoragePermissionsModel, description="Storage permissions for fs")

  # Super permissions
  sudo: bool = False

# Opens app with these options
class AppOptionsModel(BaseModel):
  sudo: bool = False
  args: list[str] = Field(default_factory=list)
  query: dict[str, Any] = Field(default_factory=dict)

# App manifest app.json in app root fs
class AppManifestModel(AppModel):
  icon: str = "icon.png"
  category: str | None = Field(None, description="App Category")
  author: str | None = Field(None, description="App Author")
  description: str | None = Field(None, description="App Description")

  source: Literal['local'] | GithubSourceModel = "local"

  # theme
  theme: str = "dark"
