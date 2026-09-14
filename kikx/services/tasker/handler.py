from typing import Any


class Handler:
  """Handle task event messages and status updates."""

  def __init__(
    self,
    handler_id: str | None,
    send_event: Any,
  ) -> None:
    self.id = handler_id
    self.send_event = send_event

  # ---------------------- Send
  async def _send(self, data: Any) -> None:
    if self.id is None:
      return

    try:
      await self.send_event(
        "tasker-data",
        {
          "id": self.id,
          "data": data,
        },
      )
    except Exception:
      pass  # Handler errors should not affect the task.

  async def send(
    self,
    status: str,
    output: Any,
  ) -> None:
    await self._send({
      "status": status,
      "output": output,
    })

  # ---------------------- Status
  async def started(self, message: Any) -> None:
    await self.send("started", message)

  async def info(self, message: Any) -> None:
    await self.send("info", message)

  async def output(self, message: Any) -> None:
    await self.send("output", message)

  async def error(self, message: Any) -> None:
    await self.send("error", message)

  async def ended(self, message: Any) -> None:
    await self.send("ended", message)


# ---------------------- Factory
def create_handler(
  handler_id: str | None,
  send_event: Any,
) -> Handler:
  return Handler(handler_id, send_event)