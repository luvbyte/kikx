from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional



# User model
class UserDataModel(BaseModel):
  name: str = Field(..., description="User full name")
  username: str = Field(..., description="Username name")
  age: Optional[int] = Field(None, description="User age")
  gender: Optional[Literal['male', 'female']] = Field(None, description="User gender")

# Auth model *
class UserAuthModel(BaseModel):
  name: str = Field(..., description="User name")
  access: str = Field(..., description="Password")
  
  access_tokens: list = Field([], description="Access Tokens")

  ui: List[str] = Field(..., description="Ui list")
  default_ui: str = Field(..., description="default one to use")
