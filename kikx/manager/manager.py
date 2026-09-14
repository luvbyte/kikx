from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

from .core import KikxManagerCore


class KikxManager:
  def __init__(self) -> None:
    self.core = KikxManagerCore("../volumes/kikxfs")
    self.router = FastAPI(lifespan=self.lifespan)

    # Setting core state
    self.router.state.core = self.core
    self.router.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
    )

  @asynccontextmanager
  async def lifespan(self, app: FastAPI):
    await self.on_start()
    yield
    await self.on_close()
  
  async def on_start(self) -> None:
    pass

  def on_connect(self, websocket: WebSocket) -> None:
    self.core.clients.append(websocket)

  async def on_data(self, websocket: WebSocket, data: dict) -> None:
    pass

  def on_disconnect(self, websocket: WebSocket) -> None:
    self.core.clients.remove(websocket)

  async def on_close(self) -> None:
    await self.core.on_close()

  async def __call__(self, scope, receive, send):
    await self.router(scope, receive, send)

