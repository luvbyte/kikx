from typing import Any, Callable, List, Optional
from pydantic import BaseModel, Field


class FuncXConfig(BaseModel):
  args: List[Any] = []
  options: dict = {}
  timeout: int = 0

class FuncXModel(BaseModel):
  name: str
  config: FuncXConfig = Field(default_factory=FuncXConfig)
