from . import js
from .ui import render, Element, Template 
from .ui.base import recursive_emit

def inject(el):
  if isinstance(el, str):
    js.html("#panel", el)
  else:
    js.html("#panel", render(el))
    
  recursive_emit(el, "injected")

def append(el):
  js.append("#panel", render(el))
  
  recursive_emit(el, "injected")


def text(el):
  js.text("#panel", el)

def clear(force=False):
  force = "true" if force else "false"
  js.run_code(f"clearPanel({force})")
  
