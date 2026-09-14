from typing import Any

from fastapi import HTTPException

from core.models.kikx import AuthModel

from lib.utils import generate_uuid


# ---------------------- Auth
class Auth:
  def __init__(self, kikx_config) -> None:
    self.kikx_config = kikx_config
    self.access_tokens: list[str] = []

  @property
  def config(self) -> AuthModel:
    return self.kikx_config.auth

  def info(self) -> dict[str, Any]:
    return {
      "tokens": self.access_tokens,
    }

  def pop_access_token(self, access_token: str) -> str | None:
    try:
      self.access_tokens.remove(access_token)
      return access_token
    except ValueError:
      return None

  def generate_access_token(self, access_key: str, ui: str) -> str:
    if access_key != self.config.access:
      raise HTTPException(status_code=401, detail="Invalid credentials")

    uid = f"{generate_uuid()}_{ui}"
    self.access_tokens.append(uid)

    return uid

  def check_access_token(self, token: str) -> bool:
    return token in self.access_tokens