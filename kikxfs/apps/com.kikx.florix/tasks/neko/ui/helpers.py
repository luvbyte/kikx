from .base import Template, Element
from typing import Optional, Dict, Iterable

# --- Helpers 
class Animate(Template):
  def __init__(self, child: Element, effect: str = "fadeIn", delay: Optional[int] = None):
    super().__init__(child)
    delay_cls = f"animate-delay-{delay * 100}" if delay else ""
    self.cls.add("animate__animated", f"animate__{effect}", delay_cls)

class Padding(Template):
  def __init__(self, child: Element, value: str = "p-1"):
    super().__init__(child)
    self.cls.add(value)

class Margin(Template):
  def __init__(self, child: Element, value: str = "m-1"):
    super().__init__(child)
    self.cls.add(value)

class Border(Template):
  def __init__(self, child: Element, value: str = "border border-black"):
    super().__init__(child)
    self.cls.add(*value.split())


class ClassBuilder:
  def __init__(self, initial: Optional[Iterable[str]] = None) -> None:
    self.cls_set: set[str] = set(initial) if initial else set()

  def add(self, *names) -> "ClassBuilder":
    for name in names:
      self.cls_set.add(name)
    return self

  def add_multiple(self, names: Iterable[str]) -> "ClassBuilder":
    self.cls_set.update(names)
    return self

  def add_if(self, name: str, condition: bool) -> "ClassBuilder":
    if condition:
      self.cls_set.add(name)
    return self

  def remove(self, name: str) -> "ClassBuilder":
    self.cls_set.discard(name)
    return self

  def toggle(self, name: str, condition: bool) -> "ClassBuilder":
    if condition:
      self.cls_set.add(name)
    else:
      self.cls_set.discard(name)
    return self

  def clear(self) -> "ClassBuilder":
    self.cls_set.clear()
    return self

  def has(self, name: str) -> bool:
    return name in self.cls_set

  def count(self) -> int:
    return len(self.cls_set)

  def merge(self, other: "ClassBuilder") -> "ClassBuilder":
    self.cls_set.update(other.cls_set)
    return self

  def clone(self) -> "ClassBuilder":
    return ClassBuilder(self.cls_set.copy())

  def done(self) -> str:
    return " ".join(sorted(self.cls_set))

class StyleBuilder:
  def __init__(self, initial: Optional[Dict[str, str]] = None) -> None:
    self.style_dict: Dict[str, str] = dict(initial) if initial else {}

  def set(self, prop: str, value: str) -> "StyleBuilder":
    self.style_dict[prop] = value
    return self

  def set_if(self, prop: str, value: str, condition: bool) -> "StyleBuilder":
    if condition:
      self.style_dict[prop] = value
    return self

  def remove(self, prop: str) -> "StyleBuilder":
    self.style_dict.pop(prop, None)
    return self

  def toggle(self, prop: str, value: str, condition: bool) -> "StyleBuilder":
    if condition:
      self.style_dict[prop] = value
    else:
      self.style_dict.pop(prop, None)
    return self

  def merge(self, other: "StyleBuilder") -> "StyleBuilder":
    self.style_dict.update(other.style_dict)
    return self

  def has(self, prop: str) -> bool:
    return prop in self.style_dict

  def clear(self) -> "StyleBuilder":
    self.style_dict.clear()
    return self

  def clone(self) -> "StyleBuilder":
    return StyleBuilder(self.style_dict.copy())

  def done(self) -> Dict[str, str]:
    return self.style_dict
