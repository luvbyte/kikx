from pathlib import Path
from fastapi import APIRouter, HTTPException
from lib.parser import parse_config
from pydantic import BaseModel, Field

from typing import List, Set


class Events:
  def __init__(self):
    self.__events = {}
  
  def add_event(self, event, func):
    if event not in self.__events:
        self.__events[event] = []
    self.__events[event].append(func)

  def emit(self, event, *args, **kwargs):
    func_list = self.__events.get(event)
    if func_list is None:
      return
    for func in func_list:
      func(*args, **kwargs)

class KikxService:
  def __init__(self, file):
    self.path = Path(file).parent
    # loading config
    self.config = {}
    self.router = APIRouter()
    
    # will be added on load [core]
    self._includes = {}
    self._events = Events()
  
  def get(self, name):
    return self._includes.get(name)

  def exception(self, status_code=404, detail=""):
    raise HTTPException(status_code=status_code, detail=str(detail))

  def get_core(self):
    core = self.get("core")
    if core is None:
      self.exception(500, "Service error: Core service not available")
    
    return core
  
  def get_client(self, request):
    client_id = request.headers.get("kikx-client-id")
    if client_id is None:
      self.exception(400, "Missing 'kikx-client-id' header")
    
    core = self.get_core()
    
    client = core.get_client(client_id)
    if client is None:
      self.exception(400, "Unauthorized client")
    
    return client

  def get_client_app(self, request):
    app_id = request.headers.get("kikx-app-id")
    if app_id is None:
      self.exception(400, "Missing 'kikx-app-id' header")
    
    core = self.get_core()
  
    client, app = core.get_client_app_by_id(app_id)
    if client is None or app is None:
      self.exception(401, "Unautorized client or app")
  
    return client, app
    
  def get_client_or_app(self, request):
    if "kikx-client-id" in request.headers:
      return self.get_client(request), None
    elif "kikx-app-id" in request.headers:
      return self.get_client_app(request)
    else:
      self.exception(400, "Unauthorized missing 'kikx-[app|client]-id' in headers")

  def on(self, event):
    def wrapper(func):
      self._events.add_event(event, func)
    return wrapper

def create_service(file):
  return KikxService(file)

