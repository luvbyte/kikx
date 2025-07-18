from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


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
