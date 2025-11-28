import re
import json
import difflib
from time import sleep
from pathlib import Path
from datetime import datetime

from neko import panel, js
from neko.ui import Div, Text, Animate, Pre
from neko.ui.helpers import ClassBuilder

from neko.lib.utils import clean, escape, get_item
from neko.widgets.fs import FSWrapper
from neko.widgets.dialogue import AlertWrapper

# basic console for simple scripts
class Console:
  def __init__(self):
    panel.clear()
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


class ConsoleThemes:
  THEMES = {
    'default': {
      'name': 'Default',
      'bg': 'bg-slate-800/60',
      'text': 'text-white',
      'scrollbar': 'scrollbar-thin scrollbar-thumb-white/20',
      'font': 'font-sans',
      'border': '',
      'extras': ''
    },
    'neon': {
      'name': 'Neon Green',
      'bg': 'bg-black/60',
      'text': 'text-green-400',
      'scrollbar': 'scrollbar-thin scrollbar-thumb-green-500/20',
      'font': 'font-mono',
      'extras': ''
    },
    'matrix': {
      'name': 'Matrix',
      'bg': 'bg-black/60',
      'text': 'text-green-300',
      'scrollbar': 'scrollbar-thin scrollbar-thumb-green-700/20',
      'font': 'font-mono',
      'extras': 'tracking-wide'
    },
    'scifi': {
      'name': 'Sci-Fi',
      'bg': 'bg-gradient-to-br from-purple-900/60 via-black to-blue-900/60',
      'text': 'text-purple-200',
      'scrollbar': 'scrollbar-thin scrollbar-thumb-purple-500/30',
      'font': 'font-sans',
      'extras': 'shadow-lg'
    },
    'solarized': {
      'name': 'Solarized Dark',
      'bg': 'bg-[#002b36]/60',
      'text': 'text-[#93a1a1]',
      'scrollbar': 'scrollbar-thin scrollbar-thumb-[#586e75]/30',
      'font': 'font-mono',
      'extras': ''
    },
  }

class ConsoleLogger:
  """Logging utilities."""
  @staticmethod
  def format_log(message):
    return f'{datetime.now().strftime("[%H:%M:%S]")} {message}'

class ConsoleHelpers:
  """Visual and formatting helpers."""
  @staticmethod
  def format_json(obj):
    return f'<pre class="text-xs whitespace-pre-wrap">{json.dumps(obj, indent=2)}</pre>'

class ConsoleWidgets:
  def __init__(self, console):
    self.console = console
    self.print = console.print
  
  def panel(self, message: str, title: str="", type='info', collapsible=False, open_by_default=True):
    color_map = {
      'info':    ('bg-blue-500/20', 'text-blue-200'),
      'success': ('bg-green-500/20', 'text-green-200'),
      'warning': ('bg-yellow-500/20', 'text-yellow-200'),
      'error':   ('bg-red-500/20', 'text-red-200'),
    }
  
    bg_class, text_class = color_map.get(type, (f'bg-{type}/20', f'text-{type}-200'))
  
    # Begin panel content
    header_html = f'<div class="font-bold text-lg">{clean(title)}</div>'
    message_html = f'<div class="whitespace-pre-wrap">{clean(str(message))}</div>'
  
    self.print(f'''
      <details {"open" if open_by_default else ""} class="p-2 {bg_class} {text_class} border-l-4 border-white/20 shadow-sm group">
        <summary class="py-2 cursor-pointer font-semibold text-white/90">{clean(title)}</summary>
        <div>{message_html}</div>
      </details>
      ''' if collapsible else f'''
      <div class="p-2 {bg_class} {text_class} shadow-sm">
        {header_html}
        {message_html}
      </div>
    ''', dom_purify=False)

  def table(self, data, headers=None, border=True, striped=True, size='sm', align="left"):
    if not data:
      self.print("[yellow]No data to display.[/yellow]")
      return
  
    is_dicts = isinstance(data[0], dict)
    if is_dicts and headers is None:
      headers = list(data[0].keys())
  
    table_classes = [
      "table-auto",
      f"text-{size}",
      "w-full",
      "border-separate",
      "border-spacing-y-1"
    ]
  
    align_class = {
      "left": "text-left",
      "center": "text-center",
      "right": "text-right"
    }.get(align, "text-left")
  
    html = [f'<div class="overflow-x-auto"><table class="{" ".join(table_classes)}">']
  
    # Header
    html.append("<thead>")
    html.append(f'<tr class="bg-black/30 text-white/80 {align_class}">')
    for header in headers:
      html.append(f'<th class="px-4 py-2 rounded-t-md whitespace-nowrap">{clean(str(header))}</th>')
    html.append("</tr></thead>")
  
    # Body
    html.append("<tbody>")
    for i, row in enumerate(data):
      row_bg = "bg-black/10" if striped and i % 2 else "bg-black/5"
      html.append(f'<tr class="{row_bg} text-white/70 hover:bg-black/20 transition {align_class}">')
  
      cells = row.values() if is_dicts else row
      for cell in cells:
        safe_html = clean(str(cell), tags=["span", "i", "b", "img"])
        html.append(f'<td class="px-4 py-2 whitespace-nowrap">{safe_html}</td>')
  
      html.append("</tr>")
    html.append("</tbody></table></div>")
  
    self.print("".join(html), dom_purify=False)

  def code_block(self, code: str, language=""):
    html = f'''
      <pre class="bg-black/30 text-white/80 text-xs font-mono py-3 overflow-auto whitespace-pre-wrap">
        <code class="language-{language}">{clean(code)}</code>
      </pre>
    '''
    self.print(html, dom_purify=False)

  def copy_box(self, preview: str, copy_text: str):
    escaped_copy = escape(copy_text).replace("'", "\\'")
    escaped_preview = clean(preview)
  
    html = f'''
      <div class="relative bg-white/5 text-white/80 rounded p-3 text-sm font-mono border border-white/10 shadow-sm">
        <!-- Clickable Preview Title -->
        <div class="cursor-pointer flex items-center justify-between gap-2"
             onclick="
              const btn = this.querySelector('span');
              navigator.clipboard.writeText('{escaped_copy}').then(() => {{
                btn.innerText = '✅ Copied!';
                btn.classList.add('text-green-400');
                setTimeout(() => {{
                  btn.innerText = '📋 Copy';
                  btn.classList.remove('text-green-400');
                }}, 1500);
              }});
            ">
          <div class="truncate">{escaped_preview}</div>
          <span class="text-xs px-2 py-1 bg-white/10 hover:bg-white/20 rounded font-semibold transition">
            📋 Copy
          </span>
        </div>
      </div>
    '''
  
    self.print(html, dom_purify=False)
  
  def stat_box(title: str, value: str, icon: str = "📊", color="blue-500"):
    return f'''
    <div class="bg-{color}/10 border-l-4 border-{color} p-3 rounded shadow text-white/80">
      <div class="text-sm">{icon} {title}</div>
      <div class="text-2xl font-bold mt-1">{value}</div>
    </div>
    '''

  def info_card(self, title: str, lines: list[str], icon="", bg="bg-slate-800/60"):
    content = "<br>".join([clean(line) for line in lines])
    self.print(f'''
      <div class="{bg} border border-white/10 rounded py-4 px-2 shadow text-white/80">
        <div class="text-lg font-bold">{icon} {clean(title)}</div>
        <div class="text-sm whitespace-pre-wrap">{content}</div>
      </div>
    ''', dom_purify=False)

  def mini_table(self, data: dict, color="white/60"):
    rows = "".join([
      f'<div class="flex justify-between py-1 border-b border-white/5 text-{color}">'
      f'<span class="font-semibold">{clean(str(k))}</span><span>{clean(str(v))}</span></div>'
      for k, v in data.items()
    ])
    self.print(f'<div class="my-2 px-3">{rows}</div>', dom_purify=False)

  def quote_box(self, message: str, author: str = "", color="purple-300"):
    self.print(f'''
    <div class="italic text-{color} bg-white/5 p-4 rounded border-l-4 border-{color} my-2">
      “{clean(message)}”
      {f'<div class="text-sm text-right mt-2">— {clean(author)}</div>' if author else ""}
    </div>
    ''', dom_purify=False)

  def diff(self, old, new, context_lines=3):
    if not isinstance(old, str): 
      old = str(old)
    if not isinstance(new, str): 
      new = str(new)
  
    old_lines = old.splitlines()
    new_lines = new.splitlines()
  
    diff_lines = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=context_lines))
  
    if not diff_lines:
      self.print("[green]No differences detected.[/green]")
      return
  
    html_lines = []
    for line in diff_lines:
      if line.startswith("+") and not line.startswith("+++"):
        html_lines.append(f'<div class="text-green-400">+ {clean(line[1:])}</div>')
      elif line.startswith("-") and not line.startswith("---"):
        html_lines.append(f'<div class="text-red-400">- {clean(line[1:])}</div>')
      elif line.startswith("@@"):
        html_lines.append(f'<div class="text-yellow-500">{clean(line)}</div>')
      else:
        html_lines.append(f'<div class="text-white/70">{clean(line)}</div>')
  
    self.print(*html_lines, dom_purify=False)
  

# super Console with more features
class SConsole:
  def __init__(self, font_size: int = 14, theme: str = "default"):
    panel.clear()
    self.font_size = font_size

    self._box = Div()
    self._history = []
    self.set_theme(theme)
    panel.inject(self.box)

  def init(self):
    pass

  @property
  def box(self):
    return self._box
  
  def set_theme(self, theme_name: str):
    """
    Apply a theme by name using the ConsoleThemes registry.
    """
    theme = ConsoleThemes.THEMES.get(theme_name)
    if not theme:
      raise Exception(f"Unknown theme: '{theme_name}'")
  
    self.box.cls.clear()
  
    # Build all theme-related classes at once
    base_classes = [
      "relative flex-1 flex flex-col overflow-y-auto overflow-x-hidden",
      theme['bg'],
      theme['text'],
      theme['scrollbar'],
      theme.get('font', 'font-sans'),
      theme.get('extras', ''),
      f"text-[{self.font_size}px]"
    ]

    # Add them in one call
    self.box.add_class(*filter(None, base_classes))
    self.active_theme = theme
  
  def set_theme_class(self, text):
    self.box.cls.clear()
    self.box.add_class(text)
  
  def append(self, el, auto_scroll=True):
    self.box.append(el)
    self.scroll_to_bottom()
  
  def replace(self, el):
    self.box.replace(el)

  def _parse_markup(self, text):
    def replacer(match):
      color = match.group(1).lower()
      content = match.group(2)
      return f'<span class="text-{color}-400">{content}</span>'
  
    pattern = re.compile(r'\[([a-zA-Z]+)\](.*?)\[/\1\]', re.DOTALL)
    return pattern.sub(replacer, text)

  def print(self, *lines, size=None, center=False, padding=None, dom_purify=True, bg=None, fg=None):
    self.append(
      Div(*[
        self._parse_markup(clean(str(line))) if dom_purify else self._parse_markup(line)
        for line in lines
      ]).add_class(
        ClassBuilder()
        .add_if(f"p-{padding}", padding)
        .add_if(f"text-[{size}px]", size)
        .add_if("text-center", center)
        .add_if(f"bg-{bg}", bg)
        .add_if(f"text-{fg}", fg)
        .done()
      )
    )
  
  def pre(self, text: str, height: str = "auto", justify: str = "start", align: str = "start", text_align: str = "start", effect: str = None) -> Pre:
    el = Pre(text)
    el.add_style("height", height)
    el.add_class(
      "text-xs", "flex", f"justify-{justify}", f"items-{align}", f"text-{text_align}"
    )
    if effect:
      el = Animate(el, effect)
    self.append(el)
    
    return el

  def pre_center(self, text: str, text_align: str = "start", effect: str = None, wait: int = 1) -> Pre:
    self.clear()
    el = self.pre(
      text, height="100%", justify="center", align="center", text_align=text_align, effect=effect
    )
    sleep(wait)
    return el
  
  def input(self, label: str = "", autohide: bool = True, focus: bool = False, effect: str = "lightSpeedInLeft") -> str:
    js.set_config("block-user-input", False)
    result = js.ask_input(label, autohide=autohide, focus=focus, effect=effect)
    js.set_config("block-user-input", True)
    return result

  def log(self, message):
    self.print(ConsoleLogger.format_log(message))

  def print_error(self, message):
    self.print(f"[red][ERROR][/red] {message}")

  def print_success(self, message):
    self.print(f"[green][OK][/green] {message}")

  def print_json(self, obj):
    self.print(ConsoleHelpers.format_json(obj), dom_purify=False)
  
  def wait(self, seconds):
    sleep(seconds)

  def hr(self):
    self.box.append('<div class="w-full bg-white min-h-[1px]"></div>')
    self.scroll_to_bottom()
  
  def br(self, times=1):
    self.append(Div("<br>" * times))

  def clear(self):
    self.box.clear()

  @property
  def fs(self):
    return FSWrapper()

  @property
  def alert(self):
    return AlertWrapper()

  def render(self):
    panel.inject(self.box)
  
  def scroll_to_bottom(self):
    self.box.scroll_to_bottom()

  def history(self, limit=20):
    return self._history[-limit:]
  
  def notify(self, message, type='info'):
    data = json.dumps({
      "type": type,
      "msg": message,
      "displayEvenActive": True
    })
    js.run_code(f"kikxApp.system.notify({data})")

  @property
  def wg(self):
    return ConsoleWidgets(self)
