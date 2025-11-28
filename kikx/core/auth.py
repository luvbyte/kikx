from uuid import uuid4
from pathlib import Path
from typing import Optional, Dict

from lib.parser import parse_config
from core.models.user_models import UserAuthModel


# -------------------------------------
# Auth Class
# -------------------------------------

class Auth:
  def __init__(self, user_config_path: Path):
    self._user_config: UserAuthModel = parse_config(user_config_path, UserAuthModel)
    self.access_tokens = []

  @property
  def user_config(self) -> UserAuthModel:
    return self._user_config
  
  def pop_access_token(self, access_token: str) -> Optional[str]:
    try:
      self.access_tokens.remove(access_token)  # remove by value (first occurrence)
      return access_token
    except ValueError:
      return None

  def generate_access_token(self, access: str) -> Optional[str]:
    if access != self.user_config.access:
      return None
    uid = uuid4().hex
    self.access_tokens.append(uid)
  
    return uid
  
  def check_access_token(self, token: str) -> Optional[str]:
    return token in self.access_tokens
