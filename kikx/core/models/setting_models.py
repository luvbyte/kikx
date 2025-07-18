from pydantic import Field
from .base import AdvancedBaseModel

from typing import Literal

class DisplayModel(AdvancedBaseModel):
  dark: bool = Field(True, description="Theme mode")
  silent: bool = Field(True, description="Silent mode")

class UserSettingsModel(AdvancedBaseModel):
  display: DisplayModel = Field(default_factory=DisplayModel, description="Display settings")
