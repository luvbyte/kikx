import asyncio
import logging
from typing import Optional, Union, Callable, Any, List

from fastapi import WebSocket

from lib.utils import send_event, is_websocket_connected

logger = logging.getLogger(__name__)


class MessageEvent:
  def __init__(self, event: str, payload: Union[dict, Callable[[], dict]]):
    self.event = event
    self.payload = payload


class Connection:
  def __init__(self) -> None:
    self.timeout: float = 10 * 60  # 10 minutes in seconds
    self.websocket: Optional[WebSocket] = None
    self.tracking: List[MessageEvent] = []
    self._disconnect_task: Optional[asyncio.Task] = None

  @property
  def is_connected(self) -> bool:
    return is_websocket_connected(self.websocket)

  async def connect(self, websocket: WebSocket) -> None:
    if not isinstance(websocket, WebSocket):
      raise TypeError("Internal Error: Invalid websocket type")

    if self.websocket is None:
      logger.info("New websocket connection established.")
      self.websocket = websocket

    elif not self.is_connected:
      logger.info("Reconnecting websocket and resending tracked messages.")
      self.websocket = websocket
      for message in self.tracking:
        await self._send_message(message)

    else:
      logger.warning("Attempt to connect while websocket is already active.")
      raise ConnectionError("WebSocket is already connected")

    self.tracking.clear()

    if self._disconnect_task:
      self._disconnect_task.cancel()
      try:
        await self._disconnect_task
        logger.debug("Previous disconnect task cancelled.")
      except asyncio.CancelledError:
        logger.debug("Disconnect task cancelled via asyncio.")
      self._disconnect_task = None

  async def _send_message(self, message: MessageEvent) -> None:
    await send_event(self.websocket, message.event, message.payload)

  async def send_event(self, event: str, payload: Union[dict, Callable[[], dict]]) -> None:
    message = MessageEvent(event, payload)

    if not self.is_connected:
      logger.debug(f"WebSocket not connected. Tracking message: {event}")
      self.tracking.append(message)
    else:
      await self._send_message(message)

  async def _on_disconnect(self, disconnect_func: Callable[[], Any], timeout: Optional[float] = None) -> None:
    async def wait_then_disconnect(wait_time: float) -> None:
      try:
        await asyncio.sleep(wait_time)
        logger.info("WebSocket idle timeout reached. Triggering disconnect.")
        await disconnect_func()
      except asyncio.CancelledError:
        logger.debug("Disconnect task was cancelled before timeout.")
        return

    wait_time = timeout if timeout is not None else self.timeout
    self._disconnect_task = asyncio.create_task(wait_then_disconnect(wait_time))