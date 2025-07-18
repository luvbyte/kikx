from pydantic import BaseModel
from uuid import uuid4
import json
import hashlib

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import os
from pathlib import Path

from typing import Dict
from core.errors import raise_error
from lib.parser import parse_config

from core.models.user_models import UserModel

def hash_strings(*strings):
  base = hashlib.md5()
  base.update("".join(strings).encode('utf-8'))
  return base.hexdigest()

SECRET_KEY = os.getenv("SECRET_KEY", uuid4().hex)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 token bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class Auth:
  def __init__(self, user_config_path: Path):
    self.user_config_path = user_config_path
    self._user_config: UserModel = parse_config(user_config_path, UserModel)

  @property
  def user_config(self):
    return self._user_config
  
  # get user_config by username, user_id, ...
  def get_user_config(self) -> UserModel:
    return self.user_config

  # user auth functions
  # Function to verify password
  def _verify_password(self, plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

  # Function to authenticate user
  def authenticate_user(self, username: str, password: str):
    user = self.get_user_config()
    if user.username != username or not self._verify_password(password, pwd_context.hash(user.password)):
      return None
    return username

  # Function to create JWT token
  def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  
  def generate_access_token(self, expires_delta: Optional[timedelta] = None):
    return self.create_access_token(data={ "sub": self.user_config.username })
  
  # check user by access_token
  def check_user_token(self, token: str):
    if token is None:
      raise_error("Token not found")
    try:
      payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
      username: str = payload.get("sub")
      user_config = self.get_user_config()
      if username is None or user_config.username != username:
        raise_error("Token Expired")
      return user_config
    except JWTError:
      raise_error("JWT Error")
    
  def check_token(self, token: str):
    try:
      return self.check_user_token(token)
    except Exception:
      return None
  
  # use this on Depends to check
  def check_user(self, request: Request):
    token = request.cookies.get("access_token")
    try:
      return self.check_user_token(token)
    except Exception:
      return None
  
  def get_user(self, access_token):
    return self.check_user_token(access_token)
