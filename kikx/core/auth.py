from typing import Any
from pathlib import Path

from fastapi import HTTPException

from lib.parser import ParseConfig
from lib.utils import generate_uuid
from core.models.user_models import UserAuthModel


# -------------------------------------
# Auth Class
# -------------------------------------

class Auth:
  def __init__(self, user_config_path: Path) -> None:
    self.config_store: ParseConfig = ParseConfig(user_config_path, UserAuthModel)
    self.access_tokens: list[str] = []

  @property
  def user_config(self) -> UserAuthModel:
    return self.config_store.data

  def save(self):
    self.config_store.save()

  def info(self) -> dict[str, Any]:
    return {
      "tokens": self.access_tokens,
      "user_config": self.user_config.model_dump()
    }

  def pop_access_token(self, access_token: str) -> str | None:
    try:
      self.access_tokens.remove(access_token)  # remove by value (first occurrence)
      return access_token
    except ValueError:
      return None

  def generate_access_token(self, access: str, ui: str) -> str:
    if access != self.user_config.access:
      raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if ui not in self.user_config.ui:
      raise HTTPException(status_code=404, detail="UI not found")

    uid = f"{generate_uuid()}_{ui}"
    self.access_tokens.append(uid)

    return uid
  
  def check_access_token(self, token: str) -> bool:
    return token in self.access_tokens
