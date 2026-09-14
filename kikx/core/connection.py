import logging
from typing import Any

from fastapi import WebSocket

from lib.utils import is_websocket_connected, send_event


logger = logging.getLogger(__name__)


# ---------------------- Message
class MessageEvent:
  def __init__(self, event: str, payload: dict) -> None:
    self.event: str = event
    self.payload: dict = payload


# ---------------------- Connection
class Connection:
  def __init__(self, name: str = "", track_messages: bool = True) -> None:
    self.name: str = name
    self.new_connection: bool = True
    self.track_messages: bool = track_messages

    self.websocket: WebSocket | None = None
    self.tracking: list[MessageEvent] = []

  @property
  def is_connected(self) -> bool:
    return is_websocket_connected(self.websocket)

  def info(self) -> dict:
    return {
      "connected": self.is_connected,
    }

  async def connect(self, websocket: WebSocket) -> None:
    if not isinstance(websocket, WebSocket):
      raise TypeError(f"{self.name}: Internal Error: Invalid websocket type")

    # Close old connection before connecting
    await self.close()

    self.new_connection = False
    self.websocket = websocket

    if not self.track_messages:
      return

    pending = self.tracking.copy()

    if pending:
      logger.info(f"{self.name}: Sending tracked messages.")

      for message in pending:
        await self._send_message(message)

    self.tracking.clear()

  async def _send_message(self, message: MessageEvent) -> None:
    await send_event(self.websocket, message.event, message.payload)

  async def send_event(self, event: str, payload: Any) -> None:
    message = MessageEvent(event, payload)

    if not self.is_connected and self.track_messages:
      logger.debug(
        f"{self.name}: WebSocket not connected. Tracking message: {event}"
      )
      self.tracking.append(message)
    else:
      await self._send_message(message)

  async def close(self, code=1000, reason=None) -> None:
    if not self.websocket:
      return

    try:
      if self.is_connected:
        await self.websocket.close(code=code, reason=reason)
        logger.info(f"Connection({self.name}) closed.")
      else:
        logger.info(f"Connection({self.name}) already closed.")
    except RuntimeError as e:
      logger.info(f"Connection({self.name}) already closed: {e}")
    except Exception as e:
      logger.exception(
        f"Connection({self.name}): Error closing websocket: {e}"
      )
    finally:
      self.websocket = None