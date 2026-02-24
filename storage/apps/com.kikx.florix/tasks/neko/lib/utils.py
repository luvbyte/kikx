import html
import bleach

from bleach import clean

# 
def sanitize_html(html_content: str) -> str:
  # Allow most common HTML tags
  allowed_tags = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "div", "span", "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "img", "table", "thead", "tbody", "tr", "td", "th",
    "ul", "ol", "li",
    "section", "article", "header", "footer",
    "strong", "em", "b", "i", "u", "pre"
  ]

  # Allow class and style on all tags
  allowed_attributes = {
    "*": ["class", "style", "id", "title", "href", "src", "alt"]
  }

  cleaned = bleach.clean(
    html_content,
    tags=allowed_tags,
    attributes=allowed_attributes,
    strip=True,  # strips disallowed tags like <script>
  )

  return cleaned

# some HTML, but remove dangerous 
# parts like <script> tags or unsafe attributes.
# example: safe_code('<b>Hello</b> <script>alert(1)</script>')
# Output: '<b>Hello</b> alert(1)'
def safe_code(html, *args, **kwargs):
  if isinstance(html, list):
    return [safe_code(code) for code in html]
  elif isinstance(html, str):
    return bleach.clean(html, *args, **kwargs)
  else:
    raise Exception("Unknown type")

# convert all HTML characters into safe text, 
# so the browser shows them literally instead of interpreting them.
# example: html.escape("<b>Hello</b>")
# Output: "&lt;b&gt;Hello&lt;/b&gt;"
def escape(text: str):
  return html.escape(text)

# Html to text
def html_to_text(text: str) -> str:
  return escape(text)

def sanitize_js_string(value: str) -> str:
  return (
    str(value)
      .replace('\\', '\\\\')   # Escape backslashes
      .replace("'", "\\'")     # Escape single quotes
      .replace('\n', '\\n')    # Escape newlines
      .replace('\r', '')       # Remove carriage returns
  )

def get_item(lst, index, default=None):
  try:
    return lst[index]
  except IndexError:
    return default

class Events:
  def __init__(self):
    self._events = {}
    self._once_handlers = {}

  def add_event(self, event_name):
    if event_name not in self._events:
      self._events[event_name] = []
      self._once_handlers[event_name] = []

  def on(self, event_name, handler):
    if event_name not in self._events:
      self.add_event(event_name)
    self._events[event_name].append(handler)

  def once(self, event_name, handler):
    if event_name not in self._events:
      self.add_event(event_name)
    self._once_handlers[event_name].append(handler)

  def remove_handler(self, event_name, handler):
    if event_name in self._events:
      try:
        self._events[event_name].remove(handler)
      except ValueError:
        pass
    if event_name in self._once_handlers:
      try:
        self._once_handlers[event_name].remove(handler)
      except ValueError:
        pass

  def off(self, event_name):
    """Remove all handlers for the event."""
    if event_name in self._events:
      self._events[event_name] = []
    if event_name in self._once_handlers:
      self._once_handlers[event_name] = []

  def _emit(self, event_name, *args, **kwargs):
    if event_name not in self._events:
      return # pass for now
      #raise ValueError(f"Event '{event_name}' is not registered.")

    # Call persistent handlers
    for handler in self._events[event_name]:
      handler(*args, **kwargs)

    # Call once-handlers and clear them
    for handler in self._once_handlers.get(event_name, []):
      handler(*args, **kwargs)
    self._once_handlers[event_name] = []
