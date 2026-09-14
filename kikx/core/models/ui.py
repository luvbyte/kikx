from pydantic import BaseModel, Field


# ---------------------- UI Config
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
    description="UI version (major.minor.patch)",
  )

  kikx_version: str = Field(
    ...,
    pattern=(
      r"^(?:(?:\^|~|~=|>=|<=|==|!=|>|<)?\d+\.\d+\.\d+)"
      r"(?:,(?:(?:>=|<=|==|!=|>|<)\d+\.\d+\.\d+))*$"
    ),
    description="Required Kikx version",
  )

  author: str | None = Field(
    None,
    description="UI author",
  )

  description: str | None = Field(
    None,
    description="UI description",
  )