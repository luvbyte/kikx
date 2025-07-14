import tempfile
import types
import base64
import os
import sys
from pathlib import Path
import pytest

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from lib import utils as du


def test_convert_to_base64():
  data = b"hello world"
  result = du.convert_to_base64(data)
  expected = base64.b64encode(data).decode("utf-8")
  assert result == expected

def test_ensure_dir_creates_directory():
  with tempfile.TemporaryDirectory() as tmpdir:
    test_path = os.path.join(tmpdir, "new_dir")
    assert not os.path.exists(test_path)
    result = du.ensure_dir(test_path)
    assert os.path.exists(test_path)
    assert result == test_path

def test_import_relative_module():
  # Built-in module for a safe test
  math_module = du.import_relative_module("math", None)
  assert math_module.sqrt(4) == 2.0


def test_is_websocket_connected_true():
  # Mock WebSocket
  class MockWebSocket(WebSocket):
    def __init__(self):
      self.client_state = WebSocketState.CONNECTED

  ws = MockWebSocket()
  assert du.is_websocket_connected(ws)
def test_is_websocket_connected_false():
  class MockWebSocket(WebSocket):
    def __init__(self):
      self.client_state = WebSocketState.DISCONNECTED

  ws = MockWebSocket()
  assert not du.is_websocket_connected(ws)
def test_is_websocket_connected_invalid_type():
  assert not du.is_websocket_connected("not_a_ws")

