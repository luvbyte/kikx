from .ui import Element, Template

class Colors:
  # Theme Colors
  primary = "bg-blue-500"         # Trustworthy & strong
  secondary = "bg-purple-500"     # Rich, deep purple for dark UI
  accent = "bg-rose-600"          # Stylish highlight
  neutral = "bg-neutral-800"      # Subtle background elements
  
  # Base Background Shades
  base_100 = "bg-zinc-900"
  base_200 = "bg-zinc-800"
  base_300 = "bg-zinc-700"
  
  # Feedback
  info = "bg-sky-500"
  success = "bg-emerald-500"
  warning = "bg-amber-500"
  error = "bg-rose-600"
  
  # Text Colors
  primary_content = "text-white"
  secondary_content = "text-purple-100"
  accent_content = "text-white"
  neutral_content = "text-white"
  base_content = "text-zinc-100"
  info_content = "text-white"
  success_content = "text-white"
  warning_content = "text-black"
  error_content = "text-white"

class Theme(Colors):
  def __init__(self):
    self.base_style = "bg-base"
    
    self.primary_style = f"{self.primary} {self.primary_content}"
    self.secondary_style = f"{self.secondary} {self.secondary_content}"
    self.accent_style = f"{self.accent} {self.accent_content}"
      
    self.info_style = f"{self.info} {self.info_content}"
    self.error_style = f"{self.error} {self.error_content}"
    self.success_style = f"{self.success} {self.success_content}"
    self.warning_style = f"{self.warning} {self.warning_content}"

  def get_style(self, style):
    return getattr(self, f"{style}_style")

  def __call__(self, style):
    return self.get_style(style)

def check_option(value, options):
  if value not in options:
    raise Exception(f"Unknown option: {value}\nAvailable: {options}")
  return value

class Label(Element):
  def __init__(self, label, style="base", align="start", size="sm", theme=Theme()):
    super().__init__(label)
    self.add_class(f"p-1 text-{align} text-{size}", theme(style))

# === Base Components ===

class Button(Element):
  def __init__(self, label, style="primary", theme=Theme()):
    super().__init__(label.upper(), tag="button")
    self.add_class("p-1 px-3 font-bold rounded-lg rounded-tl-none rounded-br-none active:scale-105 shadow-lg", theme(style))

class Row(Element):
  def __init__(self, elements, gap=0, wrap=True, theme=Theme()):
    super().__init__(*elements)
    wrap = "wrap" if wrap else "no-wrap"
    self.add_class(f"flex flex-{wrap} gap-{gap}")

class Column(Element):
  def __init__(self, elements, gap=0, wrap=True):
    super().__init__(*elements)
    wrap = "wrap" if wrap else "no-wrap"
    self.add_class(f"flex flex-col flex-{wrap} gap-{gap}")

class VCenter(Element):
  def __init__(self, element):
    super().__init__(element)
    self.add_class("flex justify-center")

class Center(Element):
  def __init__(self, element):
    super().__init__(element)
    self.add_class("w-full h-full flex justify-center items-center")

# === Display Widgets ===
class Divider(Element):
  def __init__(self):
    super().__init__()
    self.add_class("border-t my-2 border-gray-300")

class Badge(Element):
  def __init__(self, label, color="blue"):
    super().__init__(label.upper())
    self.add_class(f"inline-block text-xs font-semibold px-2 py-1 rounded-full bg-{color}-100 text-{color}-800")

class Card(Element):
  def __init__(self, *elements, style="primary", width, height, theme=Theme()):
    super().__init__(*elements)
    self.add_class(f"p-4 rounded-lg shadow-md w-[{width}] h-[{height}]", theme(style))

class Box(Element):
  def __init__(self, *elements, width=None, height=None, theme=Theme()):
    super().__init__(*elements)
    if width:
      self.add_class(f"w-[{width}]")
    if height:
      self.add_class(f"h-[{height}]")

class Image(Element):
  def __init__(self, src):
    super().__init__(tag="img")
    
    self.set_property("src", src)

# === Interactive Widgets ===

class ToggleSwitch(Element):
  def __init__(self, is_on=False):
    label = "ON" if is_on else "OFF"
    super().__init__(label)
    bg = "bg-green-500" if is_on else "bg-gray-300"
    self.add_class(f"inline-block w-12 h-6 rounded-full cursor-pointer text-white text-xs flex items-center justify-center {bg}")

class IconButton(Element):
  def __init__(self, icon, size=5, theme=Theme()):
    super().__init__(icon)
    self.add_class(f"w-{size} h-{size} flex items-center justify-center rounded-full hover:bg-gray-100", theme("primary"))

# === Layout Utilities ===
class Grid(Element):
  def __init__(self, *elements, cols=2, gap=4):
    super().__init__(*elements)
    self.add_class(f"grid grid-cols-{cols} gap-{gap}")

class List(Element):
  def __init__(self, elements):
    super().__init__(*elements)

class FullScreen(Element):
  def __init__(self, *elements):
    super().__init__(*elements)
    
    self.add_class("h-full w-full")

# === Modifiers ===

class Animate(Template):
  def __init__(self, child, effect="fadeIn"):
    super().__init__(child)

    self.add_class(f"animate__animated animate__{effect}")

class Border(Template):
  def __init__(self, element, size=1, color="base"):
    super().__init__(element)
    
    self.add_class(f"border border-{size} border-{color}-500")

class FlexGrow(Template):
  def __init__(self, element, grow=1):
    super().__init__(element)
    
    self.add_class(f"flex-{grow}")

class PadX(Element):
  def __init__(self, element, value=2):
    super().__init__(element)
    self.add_class(f"px-{value}")

class PadY(Element):
  def __init__(self, element, value=1):
    super().__init__(element)
    self.add_class(f"py-{value}")

class Padding(Element):
  def __init__(self, element, value=1):
    super().__init__(element)
    self.add_class(f"p-{value}")

class Scroll(Template):
  def __init__(self, element, scroll="auto"):
    super().__init__(element)

    self.add_class(f'overflow-{check_option(scroll, ["scroll", "hidden", "auto"])}')

class ScrollX(Template):
  def __init__(self, element, scroll="auto"):
    super().__init__(element)

    self.add_class(f'overflow-x-{check_option(scroll, ["scroll", "hidden", "auto"])}')

class ScrollY(Template):
  def __init__(self, element, scroll="auto"):
    super().__init__(element)

    self.add_class(f'overflow-y-{check_option(scroll, ["scroll", "hidden", "auto"])}')

# === Input Fields === under developmemt

class TextInput(Element):
  def __init__(self, placeholder="", value="", size="base", style="primary", theme=Theme()):
    super().__init__("", tag="input")
    self.set_property("type", "text")
    self.set_property("placeholder", placeholder)
    self.set_property("value", value)
  
    self.add_class(f"w-full px-2 p-1 rounded-lg rounded-tl-none rounded-br-none text-{size} border focus:outline-none bg-transparent")

class PasswordInput(Element):
  def __init__(self, placeholder="", value="", size="base", theme=Theme()):
    super().__init__("", tag="input")
    self.attrs["type"] = "password"
    self.attrs["placeholder"] = placeholder
    self.attrs["value"] = value
    self.add_class(f"px-3 py-2 rounded-md text-{size} border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500", theme("input"))

class TextArea(Element):
  def __init__(self, placeholder="", rows=4, value="", theme=Theme()):
    super().__init__("", tag="textarea")
    self.attrs["placeholder"] = placeholder
    self.attrs["rows"] = rows
    self.attrs["value"] = value
    self.add_class("w-full px-3 py-2 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500", theme("input"))

class Select(Element):
  def __init__(self, options, selected=None, theme=Theme()):
    super().__init__("", tag="select")
    for option in options:
      opt = Element(option, tag="option")
      opt.attrs["value"] = option
      if option == selected:
        opt.attrs["selected"] = "selected"
      self.append(opt)
    self.add_class("px-3 py-2 rounded-md border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500", theme("input"))

class Checkbox(Element):
  def __init__(self, label, checked=False):
    input_elem = Element("", tag="input")
    input_elem.attrs["type"] = "checkbox"
    if checked:
      input_elem.attrs["checked"] = "checked"
    input_elem.add_class("mr-2")

    label_elem = Element(label, tag="label")
    label_elem.append(input_elem)
    label_elem.add_class("inline-flex items-center text-sm space-x-2")

    super().__init__(label_elem)

class RadioButton(Element):
  def __init__(self, name, label, value, checked=False):
    input_elem = Element("", tag="input")
    input_elem.attrs["type"] = "radio"
    input_elem.attrs["name"] = name
    input_elem.attrs["value"] = value
    if checked:
      input_elem.attrs["checked"] = "checked"
    input_elem.add_class("mr-2")

    label_elem = Element(label, tag="label")
    label_elem.append(input_elem)
    label_elem.add_class("inline-flex items-center text-sm")

    super().__init__(label_elem)
