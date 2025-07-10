from . import panel, js
from .ui import Div, Text, Animate, Pre, Center

from .utils import get_item
from time import sleep

class Console:
  def __init__(self):
    self._panel = Div()
    self._panel.cls.add_class("w-full h-full bg-gray-600/40 text-white text-sm overflow-auto relative")

    self.auto_input_hide = True
    # user cant clear or send input
    js.run_code("blockUserClear(true); blockUserInput(true)")
    panel.inject(self._panel)
  
  @property
  def panel(self):
    return self._panel
    
  def append(self, code):
    element = self.panel.append(code)
    self.scroll_to_bottom()
    return element

  def clear(self):
    self.panel.empty()
  
  def set_auto_hide(self, value):
    if not isinstance(value, bool):
      raise Exception("Value must be 'bool'")
    self.auto_input_hide = value

  def print(self, text, center=False, effect=None, color="white", bg="transparent", size="[1rem]"):
    el = Text(text, size=size)
    class_list = [f"text-{color}", f"bg-{bg}", f"text-[{size}]"]

    if center:
      class_list.append("text-center")
    if effect:
      el = Animate(el, effect=effect)
    
    el.cls.add_class(*class_list)
    
    self.append(el)
    self.scroll_to_bottom()
  
    return el

  def pre(self, text, height="auto", justify="start", align="start", text_align="start", effect=None):
    el = Pre(text)
    el.style.add_style("height", height)
    el.cls.add_class(*["text-xs", "flex", f"justify-{justify}", f"items-{align} text-{text_align}"])
    
    if effect:
      el = Animate(el, effect)

    return self.append(el)

  def pre_center(self, text, text_align="start", effect=None, wait=1):
    self.clear()
    element = self.pre(text, height="100%", justify="center", align="center", text_align=text_align, effect=effect)
    sleep(wait)
    
    return element
   
  def render_frames(self, frames):
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

  def input(self, label="", autohide: bool | None = None):
    autohide = self.auto_input_hide if autohide is None else autohide

    js.run_code("blockUserInput(false)")
    input_text = js.ask_input(label, autohide=autohide)
    js.run_code("blockUserInput(true)")
    
    return input_text

  def br(self):
    self.append("<br>")
  
  def scroll_to_bottom(self):
    self.panel._js.scroll_to_bottom()

