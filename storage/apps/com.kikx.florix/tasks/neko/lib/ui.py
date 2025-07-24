import json
from uuid import uuid4
from typing import Callable, Union, Optional, List, Dict, Any
from . import js

VOID_TAGS = [
  "area", "base", "br", "col", "embed", "hr", "img", "input",
  "link", "meta", "source", "track", "wbr"
]

# Style abstraction
class Style:
  def __init__(
    self,
    color: str = "white",
    bg: str = "transparent",
    font_size: str = "1rem",
    line_height: str = "1rem",
    padding: str = "",
    margin: str = "",
    display: str = "",
    border: str = "",
    text_align: str = ""
  ):
    self.color = color
    self.bg = bg
    self.font_size = font_size
    self.line_height = line_height
    self.padding = padding
    self.margin = margin
    self.display = display
    self.border = border
    self.text_align = text_align

  def __call__(self) -> Dict[str, str]:
    return {
      "color": self.color,
      "background-color": self.bg,
      "font-size": self.font_size,
      "line-height": self.line_height,
      "padding": self.padding,
      "margin": self.margin,
      "display": self.display,
      "border": self.border,
      "text-align": self.text_align,
    }

class JS:
  def __init__(self):
    self.id: str = uuid4().hex
    self._injected: bool = False

  @property
  def is_injected(self) -> bool:
    return self._injected

  def func(self, code: Union[str, Callable[[], str]]) -> None:
    if not self.is_injected:
      return

    code = code() if callable(code) else code
    js.run_code(f"document.getElementById('{self.id}').{code}")

  def jfunc(self, code: Union[str, Callable[[], str]]) -> None:
    if not self.is_injected:
      return

    code = code() if callable(code) else code
    js.run_code(f"$('#{self.id}').{code}")

  def hide(self) -> None:
    self.jfunc("hide()")

  def show(self) -> None:
    self.jfunc("show()")

  def remove(self) -> None:
    self.jfunc("remove()")

  def scroll_to_bottom(self) -> None:
    js.run_code(f"scrollToBottom('#{self.id}')")

  def scroll_to_top(self) -> None:
    js.run_code(f"scrollToTop('#{self.id}')")

class ElementProp:
  def __init__(self, func: Callable[[Union[str, Callable[[], str]]], None]):
    self.prop_dict: Dict[str, str] = {}
    self._func = func

  @property
  def text(self) -> str:
    return " ".join([f'{k}="{v}"' for k, v in self.prop_dict.items()])

  def refresh(self) -> None:
    self._func(lambda: f'setAttributes({self.prop_dict})')

  def includes(self, name: str) -> bool:
    return name in self.prop_dict

  def add(self, name: str, value: str) -> None:
    self.prop_dict[name] = value
    self.refresh()

  def remove(self, name: str) -> None:
    if name in self.prop_dict:
      self.prop_dict.pop(name)
    self.refresh()

  def update(self, props: Union[Dict[str, str], str]) -> None:
    if isinstance(props, dict):
      self.prop_dict.update(props)
    elif isinstance(props, str):
      prop_pairs = [item.strip() for item in props.split(";") if item.strip()]
      prop_dict = dict(item.split("=", 1) for item in prop_pairs)
      # Clean quotes around values if present
      self.prop_dict.update({k.strip(): v.strip().strip('"').strip("'") for k, v in prop_dict.items()})
    else:
      raise Exception("Invalid props type")
    self.refresh()

  def clear(self) -> None:
    self.prop_dict.clear()
    self.refresh()

  def __str__(self) -> str:
    return self.text

class ElementStyle:
  def __init__(self, func: Callable[[Union[str, Callable[[], str]]], None]):
    self._func = func
    self.style_dict: Dict[str, str] = {}

  @property
  def text(self) -> str:
    return ";".join([f"{k}: {v}" for k, v in self.style_dict.items()])

  def refresh(self) -> None:
    self._func(lambda: f"style.cssText = '{self.text}'")
  
  def includes(self, name) -> bool:
    return name in self.style_dict

  def add(self, name: str, value: str) -> None:
    self.style_dict[name] = value
    self.refresh()

  def remove(self, name: str) -> None:
    if name in self.style_dict:
      self.style_dict.pop(name)
    self.refresh()

  def update(self, style: Union[Dict[str, str], Style, str]) -> None:
    if isinstance(style, dict):
      self.style_dict.update(style)
    elif isinstance(style, Style):
      self.style_dict.update(style())
    elif isinstance(style, str):
      style_pairs = [item.strip() for item in style.split(";") if item.strip()]
      style_dict = dict(item.split(":", 1) for item in style_pairs)
      self.style_dict.update(style_dict)
    else:
      raise Exception("Invalid style type")
    self.refresh()
  
  def clear(self):
    self.style_dict.clear()
    self.refresh()
  
  def __str__(self) -> str:
    return self.text

class ElementClass:
  def __init__(self, func: Callable[[Union[str, Callable[[], str]]], None]):
    self._func = func
    self.class_list: List[str] = []

  @property
  def text(self) -> str:
    return " ".join(self.class_list)

  def refresh(self) -> None:
    self._func(lambda: f"className = '{self.text}'")

  def includes(self, name: str) -> bool:
    return name in self.class_list

  def add(self, *names: str) -> None:
    for name in names:
      self.class_list.extend(name.split())
    self.refresh()

  def remove(self, name: str) -> None:
    if name in self.class_list:
      self.class_list.remove(name)
    self.refresh()

  def toggle(self, name: str) -> None:
    if self.includes(name):
      self.remove(name)
    else:
      self.add(name)

  def clear(self):
    self.class_list.clear()
    self.refresh()

  def __str__(self) -> str:
    return self.text

class Element:
  def __init__(self, *children: Any, tag: str = "div"):
    self._js = JS()
    self.tag = tag
    self.cls = ElementClass(self._js.func)
    self.style = ElementStyle(self._js.func)
    self.prop = ElementProp(self._js.func)
    self.children: List[Any] = list(children)

  @property
  def id(self) -> str:
    return self._js.id

  @property
  def selector(self) -> str:
    return f"#{self.id}"

  def scroll_to_top(self) -> None:
    self._js.scroll_to_top()

  def scroll_to_bottom(self) -> None:
    self._js.scroll_to_bottom()

  def set_property(self, key: str, value: str) -> None:
    self.prop.add(key, value)
    return self

  def inner_text(self, text: str) -> str:
    self.children = [text]
    js.text(self.selector, text)
    return text

  def replace(self, *elements: Any) -> 'Element':
    self.children = list(elements)
    js.html(self.selector, "".join([self._parse_element(el, self._js.is_injected) for el in elements]))
    return self

  def append(self, *elements: Any, single_text: bool = False) -> 'Element':
    self.children.extend(elements)
    if single_text:
      js.append(self.selector, "".join([self._parse_element(el, self._js.is_injected) for el in elements]))
    else:
      for el in elements:
        js.append(self.selector, self._parse_element(el, self._js.is_injected))
    return self

  def empty(self) -> 'Element':
    self.children.clear()
    js.html(self.selector, "")
    return self

  def clear(self) -> 'Element':
    return self.empty()

  def includes_class(self, name: str) -> bool:
    return self.cls.includes(name)

  def add_class(self, *names: str) -> 'Element':
    self.cls.add(*names)
    return self

  def remove_class(self, name: str) -> 'Element':
    self.cls.remove(name)
    return self

  def toggle_class(self, name: str) -> 'Element':
    self.cls.toggle(name)
    return self

  def includes_style(self, name: str) -> bool:
    return self.style.includes(name)

  def add_style(self, name: str, value: str) -> 'Element':
    self.style.add(name, value)
    return self

  def remove_style(self, name: str) -> 'Element':
    self.style.remove(name)
    return self

  def update_style(self, style: Union[Dict[str, str], Style, str]) -> 'Element':
    self.style.update(style)
    return self
  
  def refresh(self) -> 'Element':
    self.cls.refresh()
    self.style.refresh()
    return self

  def _parse_element(self, element: Any, injecting: bool = False) -> str:
    if isinstance(element, str):
      return element
    elif hasattr(element, "__code__"):
      return element.__code__(injecting)
    else:
      raise Exception("Unexpected child type")

  def __code__(self, injecting: bool = False) -> str:
    self._js._injected = injecting
    content = "".join([self._parse_element(child, injecting) for child in self.children if child is not None])
    if self.tag in VOID_TAGS:
      return f'<{self.tag} id="{self.id}" class="{self.cls.text}" style="{self.style.text}" {self.prop.text} />'
    return f'<{self.tag} id="{self.id}" class="{self.cls.text}" style="{self.style.text}" {self.prop.text}>{content}</{self.tag}>'

  def __str__(self) -> str:
    return self.__code__()

  def __call__(self, element: Union[bool, 'Element'] = True) -> str:
    if isinstance(element, bool):
      return self.__code__(element)
    elif isinstance(element, Element):
      return self.__code__(element._js._injected)
    raise Exception("Require 'Element or bool' type")

class Template:
  def __init__(self, child: Element):
    self.child = child

  def __getattr__(self, name: str) -> Any:
    return getattr(self.child, name)

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

class Box(Element):
  def __init__(self, child: Optional[Element] = None, width: str = "auto", height: str = "auto", fullscreen: bool = False):
    super().__init__(child)
    width, height = ("100%", "100%") if fullscreen else (width, height)
    self.style.add("width", width)
    self.style.add("height", height)

class Animate(Template):
  def __init__(self, child: Element, effect: str = "fadeIn", delay: Optional[int] = None):
    super().__init__(child)
    delay_str = f"animate__delay-{delay}s" if delay else ""
    self.cls.add("animate__animated", f"animate__{effect}", delay_str)

class Padding(Template):
  def __init__(self, child: Element, value: str = "0.25rem"):
    super().__init__(child)
    self.style.add("padding", value)

def render(element: Union[str, Element]) -> str:
  if isinstance(element, str):
    return Text(element).__code__(True)
  elif hasattr(element, "__code__"):
    return element.__code__(True)
  else:
    raise Exception("Unexpected Type.")
