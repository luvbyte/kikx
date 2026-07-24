from pydantic import BaseModel, Field
from typing import Literal



# User model
class UserDataModel(BaseModel):
  name: str = Field(
    ...,
    min_length=1,
    max_length=256,
    description="Name"
  )
  username: str = Field(
    ...,
    min_length=1,
    max_length=256,
    description="Username name"
  )

# Auth model
class UserAuthModel(BaseModel):
  access: str = Field(
    ...,
    min_length=1,
    max_length=256,
    description="Access key"
  )

  ui: list[str] = Field(..., description="UI's")
  default_ui: str = Field(..., description="default one to use")

