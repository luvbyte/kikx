import logging
from uuid import uuid4
from typing import List, Dict

from fastapi import Request

from lib.service import create_service
from lib.utils import file_response

# Init logger
logger = logging.getLogger("Service-Expose")
logging.basicConfig(level=logging.INFO)

srv = create_service(__file__)

class Expose:
  def __init__(self, path, extype="directory", expire: int = 120):
    self.uid = uuid4().hex
    self.extype = extype
    self.path = path

  def get(self, path: str):
    if self.extype == "directory":
      return file_response(self.path, path)

  def meta(self):
    return {
      "url": f"/service/expose/{self.uid}"
    }

class ExposeMappings:
  def __init__(self):
    self.maps = {} # id: Expose
    self.cleaner_started = False

  def get(self, uid: str, path: str):
    expose = self.maps.get(uid, None)
    if not expose:
      srv.exception(detail="UID not found")

    return expose.get(path)
  
  def create(self, path, expire):
    expose = Expose(path, expire=expire)
    mappings[expose.uid] = expose
    self.cleaner()
    return expose.meta

  # checks every 5minutes for clean up maps Expose expired objects
  def start_cleaner(self):
    # start checking

    # stop checking if 0 objects
    if len(self.maps) <= 0:
      pass

mappings = ExposeMappings()

# expire in seconds
# returns uid & direct url
@srv.router.get("/path/{path}")
def expose_path(request: Request, path: str, expire: int = 120):
  return mappings.create(path, expire)

@srv.router.get("/{uid}/{path:path}")
def serve(request: Request, uid: str, path: str):
  return mappings.get(uid)


