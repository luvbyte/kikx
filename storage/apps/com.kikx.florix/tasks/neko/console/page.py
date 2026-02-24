from time import sleep

from neko.ui import Animate, Div
from neko.lib.utils import html_to_text, sanitize_html


class PageResult:
  def __init__(self, input_):
    self._input = input_

  def get_input(self):
    return self._input
  
  @property
  def is_closed(self):
    self.get_input() == "__page__closed__"

  @property
  def is_back(self):
    self.get_input() == "__page__back__"

  @property
  def is_ok(self):
    return not self.is_closed or not self.is_back


class Page:
  def __init__(self, title=None, banner=None, back_button=False, close_button=False):
    self.title = title
    self.back_button = back_button
    self.close_button = close_button
    
    self.banner = banner

    self._input = None
  
  def to_text(self, code):
    return html_to_text(code)
  
  def sanitize(self, code):
    return sanitize_html(code)

  def set_banner(self, banner):
    self.banner = banner

  def render_back_button(self):
    if self.back_button is None:
      return ""
    
    return '''
      <button onclick="sendInput('__page__back__')" 
        class="flex items-center p-1 rounded bg-white/20">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 12 24"><path fill="currentColor" fill-rule="evenodd" d="m3.343 12l7.071 7.071L9 20.485l-7.778-7.778a1 1 0 0 1 0-1.414L9 3.515l1.414 1.414z"/></svg>
      </button>
    '''

  def render_close_button(self):
    if self.close_button is None:
      return ""
    
    return '''
      <button onclick="sendInput('__page__closed__')" 
        class="p-1 rounded bg-red-400 flex items-center">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><path fill="currentColor" d="m12 13.4l-4.9 4.9q-.275.275-.7.275t-.7-.275t-.275-.7t.275-.7l4.9-4.9l-4.9-4.9q-.275-.275-.275-.7t.275-.7t.7-.275t.7.275l4.9 4.9l4.9-4.9q.275-.275.7-.275t.7.275t.275.7t-.275.7L13.4 12l4.9 4.9q.275.275.275.7t-.275.7t-.7.275t-.7-.275z"/></svg>
      </button>
    '''

  def render_banner(self):
    if self.banner is None:
      return ""
    
    return f'''
      <div class="p-8 bg-purple-400/10 flex justify-center items-center">
        <pre>{self.sanitize(self.banner)}</pre>
      </div>
    '''

  def get_header(self):
    # If nothing to show then return empty
    if not self.title and not self.back_button and not self.close_button:
      return ""

    return f"""
      <div class="px-2 py-3 bg-blue-400/60 flex justify-between items-center gap-1">
        
        <!-- Left Side -->
        <div class="flex items-center gap-2">
          {self.render_back_button()}
          {f'<h1 class="text-md truncate">{self.to_text(self.title)}</h1>' if self.title else ''}
        </div>

        <!-- Right Side -->
        {self.render_close_button()}
      </div>
    """

  def _render(self, body):
    el = Div(
      self.get_header(),
      self.render_banner(),
      body
    )

    el.add_class("flex-1 flex flex-col overflow-hidden")
    
    return Animate(el)

  def _start_input_loop(self, console):
    while True:
      console.clear()
      console.append(self.render())

      input_ = input()
      console.clear()
  
      return PageResult(input_)


# Options page index style 
class OptionsPage(Page):
  def __init__(self, options, title="Select an option", banner=None, back_button=False, close_button=False, display_index=False):
    super().__init__(title=title, banner=banner,back_button=back_button, close_button=close_button)
    self.options = options
    self.display_index = display_index
 
  def render(self):
    options = []

    for index, option in enumerate(self.options):
      index_tag = f'<span class="min-w-2 text-blue-400">{index + 1}</span>' if self.display_index else ""
      
      code = f'<div onclick="sendInput({index + 1})" class="px-2 py-3 border-b border-b-white/40 flex items-center gap-2 active:bg-white/20 transition-colors">{index_tag}{self.to_text(option)}</div>'
      options.append(code)

    return self._render(f'<div class="flex-1 flex flex-col overflow-y-auto">{"".join(options)}</div>')
 
  def display(self, console) -> PageResult:
    return self._start_input_loop(console)


class InputPage(Page):
  def __init__(self, body=None, min_length=None, max_length=None, input_type=str, placeholder=None):
    super().__init__()

    self.error_text = None

    self.body = body
    
    self.placeholder = placeholder
    
    self.min_length = min_length
    self.max_length = max_length
    self.input_type = input_type

  def _validate(self, text):
    expected_type = self.input_type
    try:
      # Convert input to expected type
      text = self.input_type(text)
    except (ValueError, TypeError):
      raise TypeError(f"Expected type {expected_type.__name__}, got {type(text).__name__}")

    # Min length
    min_length = self.min_length
    if min_length is not None and len(text) < min_length:
      raise ValueError(f"Required minimum length is {min_length}")

    # Max length
    max_length = self.max_length
    if max_length is not None and len(text) > max_length:
      raise ValueError(f"Required maximum length is {max_length}")

    return text

  def validate(self, text: str) -> bool:
    try:
      return self._validate(text)
    except Exception as e:
      self.error_text = str(e)

    return None
  
  def render_error(self):
    return f'<div class="flex-1 flex justify-center items-center text-red-400"><h1>{self.to_text(self.error_text)}</h1></div>'

  def get_body(self):
    if self.error_text is not None:
      return self.render_error()

    if self.body is None:
      return ""
    
    return f'<div class="flex-1 flex justify-center items-center">{self.sanitize(self.body)}</div>'

  def set_body(self, body):
    self.body = body

  def render(self):
    return self._render(self.get_body())

  def display(self, console):
    while True:
      console.clear()
      console.append(self.render())

      self.error_text = None
  
      result = PageResult(console.input(self.placeholder or "", autohide=False))
      if not result.is_ok or self.validate(result.get_input()) is not None:
        console.clear()
        return result


class IframePage(Page):
  def __init__(self, url):
    super().__init__()
    self.url = url
  
  def render(self):
    return self._render(f'''
      <iframe class="flex-1" src="{self.to_text(self.url)}"></iframe>
    ''')

  def display(self, console):
    console.clear()
    console.append(self.render())
    
    result = PageResult(input())
    
    console.clear()
    
    return result


# --------- Readonly pages

# Loading page
class LoadingPage:
  def __init__(self, label=None):
    self.label = label

  def render_loading_icon(self, size=32):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24"><g fill="currentColor"><circle cx="12" cy="3.5" r="1.5"><animate attributeName="fill-opacity" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="16.25" cy="4.64" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="0.2s" to="1"/><animate attributeName="fill-opacity" begin="0.2s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="19.36" cy="7.75" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="0.4s" to="1"/><animate attributeName="fill-opacity" begin="0.4s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="20.5" cy="12" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="0.6s" to="1"/><animate attributeName="fill-opacity" begin="0.6s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="19.36" cy="16.25" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="0.8s" to="1"/><animate attributeName="fill-opacity" begin="0.8s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="16.25" cy="19.36" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="1s" to="1"/><animate attributeName="fill-opacity" begin="1s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="12" cy="20.5" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="1.2s" to="1"/><animate attributeName="fill-opacity" begin="1.2s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="7.75" cy="19.36" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="1.4s" to="1"/><animate attributeName="fill-opacity" begin="1.4s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="4.64" cy="16.25" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="1.6s" to="1"/><animate attributeName="fill-opacity" begin="1.6s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="3.5" cy="12" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="1.8s" to="1"/><animate attributeName="fill-opacity" begin="1.8s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="4.64" cy="7.75" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="2s" to="1"/><animate attributeName="fill-opacity" begin="2s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle><circle cx="7.75" cy="4.64" r="1.5" opacity="0"><set fill="freeze" attributeName="opacity" begin="2.2s" to="1"/><animate attributeName="fill-opacity" begin="2.2s" dur="2.4s" keyTimes="0;0.125;0.25;1" repeatCount="indefinite" values="1;1;0;0"/></circle></g></svg>'

  def render_label(self):
    if self.label is None:
      return ""

    return f'<h1 class="text-sm opacity-80">{html_to_text(self.label)}</h1>'

  def render(self):
    return Animate(Div(f"""
      {self.render_loading_icon()}
      <h1>{self.render_label()}</h1>
    """).add_class("bg-black/60 flex-1 flex flex-col justify-center items-center overflow-hidden"))

  def display(self, console):
    console.clear()
    console.append(self.render())

    return lambda: console.clear()

class AnimationPage:
  def __init__(self, frames=[], delay=0.6):
    self.delay = delay
    self.frames = frames

  def render(self, frame):
    return Animate(Div(f"""
      <pre>{sanitize_html(frame)}</pre>
    """).add_class("flex-1 flex flex-col justify-center items-center overflow-hidden"))

  def display(self, console):
    for frame in self.frames:
      console.clear()
      console.append(self.render(frame))
    
      sleep(self.delay)

    console.clear()
