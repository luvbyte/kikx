from fastapi import APIRouter, Request


class ServiceRouter(APIRouter):
  def __init__(self):
    super().__init__(self)
    # will be update on include
    self.srv = None

router = APIRouter()
