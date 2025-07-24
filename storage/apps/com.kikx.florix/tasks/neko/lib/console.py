from time import sleep
from . import panel, js
from .utils import get_item
from .ui import Div, Text, Animate, Pre, Center

class Console:
  def __init__(self):
    self._panel = Div()
    self._panel.add_class(
      "w-full h-full bg-gray-600/40 text-white text-sm overflow-auto relative"
    )
    panel.inject(self._panel)

  @property
  def panel(self) -> Div:
    return self._panel

  def append(self, code) -> 'Console':
    self.panel.append(code)

    return self

  def clear(self) -> 'Console':
    self.panel.empty()
    
    return self

  def print(
    self, 
    text: str, 
    center: bool = False, 
    effect: str = None, 
    color: str = "white", 
    bg: str = "transparent", 
    size: str = "[1rem]"
  ) -> Text:
    el = Text(text, size=size)
    class_list = [f"text-{color}", f"bg-{bg}", f"text-[{size}]"]
    if center:
      class_list.append("text-center")
    if effect:
      el = Animate(el, effect=effect)
    el.add_class(*class_list)
    self.append(el)
    self.scroll_to_bottom()

    return el

  def pre(
    self, 
    text: str, 
    height: str = "auto", 
    justify: str = "start", 
    align: str = "start", 
    text_align: str = "start", 
    effect: str = None
  ) -> Pre:
    el = Pre(text)
    el.add_style("height", height)
    el.add_class(
      "text-xs", "flex", f"justify-{justify}", f"items-{align}", f"text-{text_align}"
    )
    if effect:
      el = Animate(el, effect)
    self.append(el)
    
    return el

  def pre_center(
    self, 
    text: str, 
    text_align: str = "start", 
    effect: str = None, 
    wait: int = 1
  ) -> Pre:
    self.clear()
    el = self.pre(
      text, height="100%", justify="center", align="center", text_align=text_align, effect=effect
    )
    sleep(wait)
    return el

  def render_frames(self, frames: str) -> None:
    collector = []
    for line in frames.split("\n"):
      split_line = line.split()
      if line.startswith("!-!"):
        self.pre_center(
          "\n".join(collector), 
          effect=get_item(split_line, 2, "fadeIn"),
          wait=int(get_item(split_line, 1, 1))
        )
        collector.clear()
      else:
        collector.append(line)

  def input(
    self, 
    label: str = "", 
    autohide: bool = True, 
    focus: bool = False, 
    effect: str = "lightSpeedInLeft"
  ) -> str:
    js.set_config("block-user-input", False)
    result = js.ask_input(label, autohide=autohide, focus=focus, effect=effect)
    js.set_config("block-user-input", True)
    return result

  def br(self) -> None:
    self.append("<br>")

  def scroll_to_bottom(self) -> None:
    self.panel._js.scroll_to_bottom()
