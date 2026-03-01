from neko.ui import Div, Text, Animate
from neko.app import JApp

from typing import List
from pathlib import Path

from neko import panel

from neko.lib.utils import clean

class Alert(Div):
  def __init__(self, message: str, title=None, atype="info", confirm=False):
    super().__init__()

    styles = {
      "info": "bg-blue-800/90 to-slate-900 text-cyan-200 rounded-lg shadow-xl border border-cyan-400",
      "error": "bg-red-800/90 to-slate-900 text-cyan-200 rounded-lg shadow-xl border border-red-400",
      "warning": "bg-yellow-800/90 to-slate-900 text-cyan-200 rounded-lg shadow-xl border border-yellow-400",
      "success": "bg-green-800/90 to-slate-900 text-cyan-200 rounded-lg shadow-xl border border-green-400",
    }
    
    animation = {
      "info": None,
      "error": "headShake",
      "warning": "flash",
      "success": "jello"
    }.get(atype, None)

    self.add_class("absolute w-full h-full inset-0 flex items-center justify-center overflow-hidden")

    self.body = Div(f"""
        <!-- Header -->
        { f'<div class="text-sm text-center p-2 font-semibold rounded-t-lg tracking-widest border-b border-white/30">{clean(title)}</div>' if title else '' }
        <!-- Body -->
        <div class="flex-1 {"min-h-[100px]" if not confirm else ""} p-4 text-sm font-mono tracking-wide">
          {clean(message)}
        </div>
          <!-- Buttons (if confirm dialog) -->
          {'''
          <div class="flex p-4 justify-end gap-2">
            <button onclick="sendInput('yes')" class="px-4 py-1 text-white rounded bg-green-600/80 active:scale-110 transition">Yes</button>
            <button onclick="sendInput('no')" class="px-4 py-1 text-white rounded bg-red-600/80 active:scale-110 transition">No</button>
          </div>
          ''' if confirm else ''}
    """).add_class('w-4/5 flex flex-col h-auto bg-gradient-to-rb transition-all duration-500').add_class(styles.get(atype, styles["info"]))
    
    self.on("injected", self.on_injected)

    self.append(Animate(self.body, animation))
    self.confirm = confirm

  def on_injected(self):
    self.bind("click", "if(this === event.target) sendInput('...')")

  def show(self):
    panel.append(self)
    
    while True:
      result = input().strip()
      if result == "..." and self.confirm:
        self.replace(Animate(self.body, "shakeX"))
      else:
        break
    self._js.jfunc("remove()")
    return result if self.confirm else None

class AlertWrapper:
  def confirm(self, message, title=None):
    return Alert(message, title, "info", True).show()
  
  def info(self, message, title=None, confirm=False):
    return Alert(message, title, "info", confirm).show()

  def error(self, message, title=None, confirm=False):
    return Alert(message, title, "error", confirm).show()

  def warning(self, message, title=None, confirm=False):
    return Alert(message, title, "warning", confirm).show()

  def success(self, message, title=None, confirm=False):
    return Alert(message, title, "success", confirm).show()
  
  def __call__(self, *args, **kwargs):
    return self.info(*args, **kwargs)
