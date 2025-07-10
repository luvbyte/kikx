from lib.parser import parse_config
from fastapi import APIRouter
from pathlib import Path
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

class KikxK1Service:
  def __init__(self, file):
    self.path = Path(file).parent
    # loading config
    self.config = {}
    self.router = APIRouter()
  
    self._includes = {}
    self._events = Events()
  
  def get(self, name):
    return self._includes.get(name)

  @property
  def kikx_core(self):
    return self._includes["core"]

  def on(self, event):
    def wrapper(func):
      self._events.add_event(event, func)
    return wrapper

def create_service(file):
  return KikxK1Service(file)

