from pydantic import BaseModel
from typing import Any

# Github source model for apps
class GithubSourceModel(BaseModel):
  url: str
  owner: str
  repo: str
  tag: str | None


class EventPayloadModel(BaseModel):
  event: str
  payload: dict[str, Any]

