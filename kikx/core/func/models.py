from pydantic import BaseModel, Field

from typing import Any


class FuncXConfig(BaseModel):
  args: list[Any] = Field(default_factory=list)
  options: dict[str, Any] = Field(default_factory=dict)
  timeout: int = 0

class FuncXModel(BaseModel):
  name: str
  config: FuncXConfig = Field(default_factory=FuncXConfig)
