import json
from .ui import Text
from .lib.utils import clean
from .lib.crypto import text_to_base62, base62_to_text

from typing import Any


def ref(text: str) -> Text:
  return Text(clean(text))

class JApp:
  def __init__(self, *args: Any, **kwargs: Any):
    self.init(*args, **kwargs)

  def init(self, *args: Any, **kwargs: Any) -> Any:
    pass
  
  def create_event(self, prefix, *args, js_args=[]):
    serialized_args = json.dumps([str(arg) for arg in args])
    hash_value = text_to_base62(serialized_args)  # Should return a string
    js_args_str = f", {', '.join(js_args)}" if js_args else ""
    return f"sendArgsJSON('{prefix}:{hash_value}'{js_args_str})"
  
  def bind(self, name: str, *args, extra=[]) -> str:
    return self.create_event(name, *args, js_args=extra)
  
  def send(self, text, raw=False):
    return f"sendInput({text})" if raw else f"sendInput('{text}')"

  def on(self, name, *args, event="click", ev=False):
    return f'on{event}="{self.bind("on_" + name, *args, extra=["utils.getEventObject(event)"] if ev else [])}"'

  def _on_event_data(self, event_hash, *args):
    # may raise error
    event, _hash_text = event_hash.split(":")
    return getattr(self, event)(*json.loads(base62_to_text(_hash_text)), *args)

  def default(self, text):
    pass

  def clean(self, text):
    return clean(text)

  def startloop(self) -> None:
    while True:
      text: str = input().strip()
      try:
        # [on:hash, ...] - python list
        if self._on_event_data(*json.loads(text)):
          break
      except json.JSONDecodeError:
        if self.default(text):
          break
