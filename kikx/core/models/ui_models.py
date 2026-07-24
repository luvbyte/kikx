from pydantic import Field, BaseModel

class UIConfigModel(BaseModel):
  name: str = Field(
    ...,
    min_length=1,
    max_length=20,
    description="UI name",
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

  author: str | None = Field(None, description="App Author")
  description: str | None = Field(None, description="App Description")

