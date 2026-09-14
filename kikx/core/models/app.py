from typing import Any, Literal

from pydantic import Field, field_validator

from .base import StrictBaseModel
from .pkg import GithubSourceModel
from .services import ServiceConfigModel


# ---------------------- Services
KIKX_SERVICE = Literal[
  "system",
  "fs",
  "os",
  "kv",
  "proxy",
  "micro",
  "tasker",
]


# ---------------------- App Iframe
AppFrameSandboxFlag = Literal[
  "allow-scripts",
  "allow-same-origin",
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

AppFrameAllowFeature = Literal[
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


# ---------------------- System Permissions
ACCESS_LIST = Literal[
  "alerts",
  "sessions",
  "kpm",
  "invoke",
]


class AppSystemPermissionsModel(StrictBaseModel):
  access: list[ACCESS_LIST] = Field(default_factory=list)

  @field_validator("access")
  @classmethod
  def deduplicate(cls, value: list[ACCESS_LIST]) -> list[ACCESS_LIST]:
    return list(dict.fromkeys(value))

  def check(self, permission: ACCESS_LIST) -> bool:
    return permission in self.access


# ---------------------- Iframe
class AppFrameModel(StrictBaseModel):
  allowfullscreen: bool = Field(
    False,
    description="Allow fullscreen mode",
  )

  sandbox: list[AppFrameSandboxFlag] = Field(default_factory=list)
  allow: list[AppFrameAllowFeature] = Field(default_factory=list)

  loading: Literal["lazy", "eager"] = Field(
    "eager",
    description="Lazy or eager loading",
  )

  referrerpolicy: Literal[
    "no-referrer",
    "origin",
    "unsafe-url",
  ] = Field(
    "no-referrer",
    description="Controls referrer information",
  )

  canGoBack: bool = False

  @field_validator("sandbox", "allow")
  @classmethod
  def deduplicate(
    cls,
    value: list[str],
  ) -> list[str]:
    return list(dict.fromkeys(value))

  def get_dict(self) -> dict[str, Any]:
    return {
      "allowfullscreen": self.allowfullscreen,
      "sandbox": " ".join(self.sandbox),
      "allow": "; ".join(self.allow),
      "loading": self.loading,
      "referrerpolicy": self.referrerpolicy,
      "canGoBack": self.canGoBack,
    }


# ---------------------- Connection
class ConnectionModel(StrictBaseModel):
  tracking: bool = True


# ---------------------- App Config
class AppModel(StrictBaseModel):
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
    pattern=(
      r"^(?:(?:\^|~|~=|>=|<=|==|!=|>|<)?\d+\.\d+\.\d+)"
      r"(?:,(?:(?:>=|<=|==|!=|>|<)\d+\.\d+\.\d+))*$"
    ),
    description="Required Kikx version",
  )

  # Frontend permissions
  iframe: AppFrameModel = Field(
    default_factory=AppFrameModel,
    description="Iframe permissions",
  )

  # Service permissions
  services: list[KIKX_SERVICE] = Field(default_factory=list)

  # Service config
  service_config: ServiceConfigModel | None = None

  # System permissions
  system: AppSystemPermissionsModel = Field(
    default_factory=AppSystemPermissionsModel,
    description="System permissions",
  )

  # Connection config
  connection: ConnectionModel = Field(default_factory=ConnectionModel)

  # Sudo permissions
  sudo: bool = False

  @field_validator("services")
  @classmethod
  def deduplicate(cls, value: list[KIKX_SERVICE]) -> list[KIKX_SERVICE]:
    return list(dict.fromkeys(value))

  def has_service(self, name: KIKX_SERVICE) -> bool:
    return name in self.services

  def get_service_config(self, name: str) -> Any | None:
    if self.service_config is None:
      return None

    return getattr(self.service_config, name, None)


# ---------------------- App Manifest
class AppManifestModel(AppModel):
  web: str = "www"

  icon: str = Field(
    "icon.png",
    description="App icon",
  )

  splash: str | None = Field(
    None,
    description="Splash screen image",
  )

  category: str | None = Field(
    None,
    description="App category",
  )

  author: str | None = Field(
    None,
    description="App author",
  )

  description: str | None = Field(
    None,
    description="App description",
  )

  source: Literal["local"] | GithubSourceModel = Field(
    "local",
    description="App installed source",
  )

  theme: str = Field(
    "dark",
    description="App UI theme",
  )


# ---------------------- Share
class AppShareOption(StrictBaseModel):
  item: str
  itemType: Literal["text", "link", "file"]


# ---------------------- App Options
class AppOptionsModel(StrictBaseModel):
  sudo: bool = False

  args: list[Any] = Field(default_factory=list)
  query: dict[str, Any] = Field(default_factory=dict)

  share: AppShareOption | None = None