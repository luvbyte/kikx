import os
import json
import hashlib
from uuid import uuid4
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from pydantic import BaseModel

from core.errors import raise_error
from lib.parser import parse_config
from core.models.user_models import UserAuthModel


# -------------------------------------
# Configurations
# -------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", uuid4().hex)
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# -------------------------------------
# Utility Functions
# -------------------------------------

def hash_strings(*strings: str) -> str:
  """
  Hash a sequence of strings into a single MD5 hash.
  """
  base = hashlib.md5()
  base.update("".join(strings).encode("utf-8"))
  return base.hexdigest()

# -------------------------------------
# Auth Class
# -------------------------------------

class Auth:
  def __init__(self, user_config_path: Path):
    """
    Initialize the Auth system with a path to a user config file.
    """
    self.user_config_path = user_config_path
    self._user_config: UserAuthModel = parse_config(user_config_path, UserAuthModel)

  @property
  def user_config(self) -> UserAuthModel:
    """
    Access the loaded user configuration.
    """
    return self._user_config

  def get_user_config(self) -> UserAuthModel:
    """
    Retrieve the parsed user configuration.
    """
    return self.user_config

  def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
    """
    Verify that the provided plain password matches the stored hash.
    """
    return pwd_context.verify(plain_password, hashed_password)

  def authenticate_user(self, username: str, password: str) -> Optional[str]:
    """
    Authenticate a user by username and password.
    Returns username if successful, otherwise None.
    """
    user = self.get_user_config()
    if user.username != username:
      return None
    # The stored password is plain in config, so we hash and compare
    if not self._verify_password(password, pwd_context.hash(user.password)):
      return None
    return username

  def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token with optional expiration override.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=self._user_config.expire))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

  def generate_access_token(self, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a token for the current configured user.
    """
    return self.create_access_token(data={"sub": self.user_config.username}, expires_delta=expires_delta)

  def check_user_token(self, token: str) -> UserAuthModel:
    """
    Decode and validate a JWT token.
    Raises on invalid or expired token.
    """
    if token is None:
      raise_error("Token not found")
    try:
      payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
      username: str = payload.get("sub")
      user_config = self.get_user_config()
      if not username or user_config.username != username:
        raise_error("Token expired or invalid")
      return user_config
    except JWTError:
      raise_error("JWT error: invalid or malformed token")

  def check_token(self, token: Optional[str]) -> Optional[UserAuthModel]:
    """
    Silently validate a token, returning None if invalid.
    Useful for public or unauthenticated access fallback.
    """
    try:
      return self.check_user_token(token)
    except Exception:
      return None

  def check_user(self, request: Request) -> Optional[UserAuthModel]:
    """
    Extract and validate user token from cookies.
    Used as a dependency in protected routes.
    """
    token = request.cookies.get("access_token")
    return self.check_token(token)

  def get_user(self, access_token: str) -> UserAuthModel:
    """
    Retrieve the user configuration associated with a given access token.
    """
    return self.check_user_token(access_token)

