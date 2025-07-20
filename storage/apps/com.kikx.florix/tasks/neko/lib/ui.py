import json
from uuid import uuid4
from . import js

VOID_TAGS = [
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr"
]


class JS:
  def __init__(self):
    self.id = uuid4().hex
    self._injected = False
  
  @property
  def is_injected(self):
    return self._injected

  # js function
  def func(self, code):
    if not self.is_injected:
      return 

    code = code() if callable(code) else code
    js.run_code(f"document.getElementById('{self.id}').{code}")
  
  # jquery functions
  def jfunc(self, code):
    if not self.is_injected:
      return
      #raise Exception("Element not injected")

    code = code() if callable(code) else code
    js.run_code(f"$('#{self.id}').{code}")
  
  def hide(self):
    self.jfunc("hide()")

  def show(self):
    self.jfunc("show()")
  
  def remove(self):
    self.jfunc("remove()")
  
  def scroll_to_bottom(self):
    js.run_code(f"scrollToBottom('#{self.id}')")
  
  def scroll_to_top(self):
    js.run_code(f"scrollToTop('#{self.id}')")

# dep
class Style:
  def __init__(self, color="white", bg="transparent", font_size="1rem", line_height="1rem", padding=""):
    self.color = color
    self.bg = bg
    
    self.padding = padding
    self.font_size = font_size
    self.line_height = line_height
  
  def __call__(self):
    return {
      "color": self.color,
      "padding": self.padding,
      "background-color": self.bg,
      "font-size": self.font_size,
      "line_height": self.line_height
    }

class ElementStyle:
  def __init__(self, func):
    self._func = func
    self.style_dict = {}

  @property
  def css_text(self):
    return ";".join([f"{k}: {v}" for k, v in self.style_dict.items()])
  
  def refresh(self):
    self._func(lambda: f"style.cssText = '{self.css_text}'")

  def add_style(self, name, value):
    self.style_dict.update({ name: value })
    self.refresh()
  
  def set_style(self, style):
    self.style_dict.update(style())
    self.refresh()

class ElementClass:
  def __init__(self, func):
    self._func = func
    self.class_list = []

  @property
  def class_text(self):
    return " ".join(self.class_list)
  
  def refresh(self):
    self._func(lambda: f"className = '{self.class_text}'")
  
  def has_class(self, name):
    return name in self.class_list
  
  # js functions
  # implement that auto splits text 
  def add_class(self, *names):
    # class_list = [name for name in names]
    for name in names:
      self.class_list.extend(name.split())

    self.refresh()
  
  def remove_class(self, name):
    self.class_list.remove(name)
    self.refresh()
  
  def toggle_class(self, name):
    if self.has_class(name):
      self.remove_class(name)
    else:
      self.add_class(name)

# Elements
class Element:
  def __init__(self, *children, tag="div"):
    self._js = JS()

    self.tag = tag
    # self.end_tag = "/>" if tag in ["img", "input"] else f"</{self.tag}>"

    self.cls = ElementClass(self._js.func)
    self.style = ElementStyle(self._js.func)

    self.properties = {}  # Holds additional HTML attributes

    self.children = list(children)

  @property
  def id(self):
    return self._js.id
  
  @property
  def selector(self):
    return f"#{self.id}"
  
  def scroll_to_top(self):
    self._js.scroll_to_top()

  def scroll_to_bottom(self):
    self._js.scroll_to_bottom()

  def set_property(self, key, value):
    self.properties[key] = value
  
  def inner_text(self, text):
    self.children = [text]
    js.text(self.selector, text)
    
    return text

  def replace(self, element):
    self.children = [element]
    js.html(self.selector, self._parse_element(element, self._js.is_injected))
    
    return element
  
  def append(self, element):
    self.children.append(element)
    js.append(self.selector, self._parse_element(element, self._js.is_injected))
    
    return element

  def empty(self):
    self.children.clear()
    js.html(self.selector, "")

  def _parse_element(self, element, injecting=False):
    if isinstance(element, str):
      return element
    elif hasattr(element, "__code__"):
      return element.__code__(injecting)
    else:
      raise Exception("Unexpected type")

  def __code__(self, injecting=False):
    self._js._injected = injecting

    # Build property string from dictionary
    prop_text = " ".join(f'{k}="{v}"' for k, v in self.properties.items())
    # Join all child elements as string
    content = "".join([self._parse_element(child, injecting) for child in self.children if child is not None])
    
    # Self-closing tag
    if self.tag in VOID_TAGS:
      return f'<{self.tag} id="{self.id}" class="{self.cls.class_text}" style="{self.style.css_text}" {prop_text} />'
  
    # Normal tag
    return f'<{self.tag} id="{self.id}" class="{self.cls.class_text}" style="{self.style.css_text}" {prop_text}>{content}</{self.tag}>'


class Template:
  def __init__(self, child):
    self.child = child

  def __getattr__(self, name):
    return getattr(self.child, name)

class Div(Element):
  def __init__(self, *children):
    super().__init__(*children)

class Pre(Element):
  def __init__(self, *children):
    super().__init__(*children, tag="pre")

class Center(Element):
  def __init__(self, *children):
    super().__init__(*children)
    
    self.cls.add_class(*["w-full", "h-full", "flex", "items-center", "justify-center"])

# check child type
class Text(Element):
  def __init__(self, text="", size=None, center=False):
    super().__init__(str(text))
    
    class_list = []
    if size:
      class_list.append(f"text-{size}")
    if center:
      class_list.append("text-center")
    
    self.cls.add_class(*class_list)

  def set_text(self, text):
    self.set_children(text)

# -------- template
class Box(Element):
  def __init__(self, child=None, width="auto", height="auto", fullscreen=False):
    super().__init__(child)

    width, height = ("100%", "100%") if fullscreen else (width, height)

    self.style.add_style("width", width)
    self.style.add_style("height", height)

class Animate(Template):
  def __init__(self, child, effect="fadeIn", delay=None):
    """ delay in seconds - 1 to 5 for now """
    super().__init__(child)
    
    delay = "" if delay is None else f"animate__delay-{delay}s"
    self.cls.add_class(f"animate__animated animate__{effect} {delay}")

class Padding(Template):
  def __init__(self, child, value="0.25rem"):
    super().__init__(child)

    self.style.add_style("padding", value)


def render(element: Element):
  if isinstance(element, str):
    return Text(element).__code__(True)
  elif hasattr(element, "__code__"):
    return element.__code__(True)
  else:
    raise Exception("Unexpected Type.")

