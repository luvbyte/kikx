from pydantic import Field
from .base import AdvancedBaseModel

from typing import Literal, Optional



class DisplayModel(AdvancedBaseModel):
  dark: bool = Field(True, description="Theme mode")

class SoundModel(AdvancedBaseModel):
  silent: bool = Field(True, description="Silent mode")

class UserSettingsModel(AdvancedBaseModel):
  display: DisplayModel = Field(default_factory=DisplayModel, description="Display settings")
  sound: SoundModel = Field(default_factory=SoundModel, description="Sound settings")
