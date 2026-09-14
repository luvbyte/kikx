from pydantic import BaseModel


# ---------------------- GitHub Source
class GithubSourceModel(BaseModel):
  url: str
  owner: str
  repo: str
  tag: str | None = None
