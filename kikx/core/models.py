# core router models
from pydantic import BaseModel
from typing import List, Dict

from core.func.func import FuncXModel

# models used for app opening routes
# /open-app
class CloseAppModel(BaseModel):
  app_id: str
  client_id: str
# /close-app
class OpenAppModel(BaseModel):
  name: str
  client_id: str
  
class AppsListModel(BaseModel):
  client_id: str
