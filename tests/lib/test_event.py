import pytest
import asyncio
from kikx.lib.event import Events


# ----------------------------------
# Test: add_event registers handlers
# ----------------------------------

def test_add_event_registers_handler():
  events = Events()

  def handler():
    pass

  events.add_event("test", handler)

  assert "test" in events._events
  assert handler in events._events["test"]


# ----------------------------------
# Test: emit_order executes sync handler
# ----------------------------------

@pytest.mark.asyncio
async def test_emit_order_sync():
  events = Events()
  result = []

  def handler(value):
    result.append(value)

  events.add_event("sync_event", handler)

  await events.emit_order("sync_event", 10)

  assert result == [10]


# ----------------------------------
# Test: emit_order executes async handler
# ----------------------------------

@pytest.mark.asyncio
async def test_emit_order_async():
  events = Events()
  result = []

  async def handler(value):
    await asyncio.sleep(0.01)
    result.append(value)

  events.add_event("async_event", handler)

  await events.emit_order("async_event", 20)

  assert result == [20]


# ----------------------------------
# Test: emit runs async handlers concurrently
# ----------------------------------

@pytest.mark.asyncio
async def test_emit_parallel():
  events = Events()
  result = []

  async def handler1():
    await asyncio.sleep(0.01)
    result.append("a")

  async def handler2():
    await asyncio.sleep(0.01)
    result.append("b")

  events.add_event("parallel", handler1)
  events.add_event("parallel", handler2)

  await events.emit("parallel")

  assert sorted(result) == ["a", "b"]


# ----------------------------------
# Test: emit_async runs in background
# ----------------------------------

@pytest.mark.asyncio
async def test_emit_async_background():
  events = Events()
  result = []

  async def handler():
    await asyncio.sleep(0.01)
    result.append("done")

  events.add_event("bg", handler)

  await events.emit_async("bg")

  # Give background task time to run
  await asyncio.sleep(0.05)

  assert result == ["done"]


# ----------------------------------
# Test: error handling does not crash
# ----------------------------------

@pytest.mark.asyncio
async def test_emit_async_error_handling(capfd):
  events = Events()

  async def bad_handler():
    raise ValueError("Boom")

  events.add_event("error", bad_handler)

  await events.emit_async("error")

  await asyncio.sleep(0.05)

  captured = capfd.readouterr()
  assert "Event handler error" in captured.out