from fastapi import Request


def get_core(request: Request):
  return request.app.state.core

