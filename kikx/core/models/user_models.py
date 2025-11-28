from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


class UserDataModel(BaseModel):
  name: str = Field(..., description="User full name")
  username: str = Field(..., description="Username name")
  age: int = Field(..., description="User age")
  gender: Literal['male', 'female'] = Field(..., description="User gender")

class UserAuthModel(BaseModel):
  name: str = Field(..., description="User name")
  access: str = Field(..., description="Password")
  
  access_tokens: list = Field([], description="Access Tokens")

  ui: List[str] = Field(..., description="Ui list")
  default_ui: str = Field(..., description="default one to use")
