from .base import Element
from .. import js
from typing import Optional, Any, Union

class Div(Element):
  def __init__(self, *children: Any):
    super().__init__(*children)

class Pre(Element):
  def __init__(self, *children: Any):
    super().__init__(*children, tag="pre")

class Center(Element):
  def __init__(self, *children: Any):
    super().__init__(*children)
    self.cls.add("w-full", "h-full", "flex", "items-center", "justify-center")

class Text(Element):
  def __init__(self, text: Union[str, int, float] = "", size: Optional[str] = None, center: bool = False):
    super().__init__(str(text))
    class_list = []
    if size:
      class_list.append(f"text-{size}")
    if center:
      class_list.append("text-center")
    self.cls.add(*class_list)

  def set_text(self, text: str) -> None:
    self.children = [text]
    js.text(self.selector, text)

class Box(Element):
  def __init__(self, child: Optional[Element] = None, width: str = "auto", height: str = "auto", fullscreen: bool = False):
    super().__init__(child)
    width, height = ("100%", "100%") if fullscreen else (width, height)
    self.style.add("width", width)
    self.style.add("height", height)
