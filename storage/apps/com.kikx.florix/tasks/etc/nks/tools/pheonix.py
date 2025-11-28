from urllib.parse import urljoin
import argparse
import json
from pathlib import Path

from neko.console import SConsole
from neko.ui import Animate, Div, Pre, Element


console = SConsole()


BANNER = r"""
＜￣｀ヽ、                        ／￣＞
      ゝ、   ＼     /\/\   ノ      /´
          ゝ、  `  (0.0)      ／
              >          ,ノ
                ∠_,,,/´
"""

def display_banner(center=False):
  console.append(Animate(Pre(BANNER).add_class("text-xs flex p-2 justify-center items-center")))
  console.print("[ Pheonix ] [red]0.0.1[/red] @[blue]luv[/blue]", center=True)
  console.br()
  console.wait(1)

def intro() -> str:
  display_banner()
  
  console.print("TYPE [purple]URL[/purple] TO [red]SCAN[/red]", center=True, size=14)
  console.br()

  # Inputs
  url_input = Element(tag="input").add_class("p-2 w-full bg-transparent rounded border focus:outline-none").set_property("placeholder", "Target URL (e.g., http://example.com)")
  timeout_input = Element(tag="input").add_class("p-2 w-full bg-transparent rounded border focus:outline-none").set_property("placeholder", "Timeout (sec)").set_property("type", "number")

  # Wordlist selector (readonly input)
  wordlist_input = Element(tag="input").add_class("p-2 w-full bg-transparent rounded border focus:outline-none cursor-pointer").set_property("readonly", True).set_property("placeholder", "Click to select wordlist")

  # Error display
  error_div = Div().add_class("text-red-500 text-sm font-bold")

  # Submit button
  button = Div("START").add_class(
    "w-full font-bold p-2 rounded text-xs text-center bg-gradient-to-b from-purple-400/80 to-blue-400 active:bg-white"
  )

  # UI layout
  form_layout = Div(
    url_input(),
    timeout_input(),
    wordlist_input(),
    error_div(),
    button()
  ).add_class("px-2 flex flex-col gap-2")

  console.append(Animate(form_layout))
  
  wordlist_input.bind("click", "sendInput('file-select')")
  # JS binding — with wordlist
  button.bind("click", f"""
    const url = $('{url_input.selector}').val().trim()
    if (!url) {{
      $('{error_div.selector}').text("Please enter a valid URL.")
      return
    }}
    $('{error_div.selector}').text("")  // Clear previous error

    const payload = {{
      url,
      timeout: parseInt($('{timeout_input.selector}').val()) || 5,
      wordlist: $('{wordlist_input.selector}').val()
    }}
    sendInput(JSON.stringify(payload))
  """)

  # Handle input from backend
  while True:
    text = input()
    if text == "file-select":
      file_path = console.fs.ask_file("Select wordlist")
      if len(file_path) > 0:
        wordlist_input._js.jfunc(f"val({json.dumps(str(file_path[0]))})")
    else:
      return json.loads(text)

class Pheonix:
  def __init__(self, options: dict):
    import requests
    #from requests import get, RequestException

    self.url = options.get("url")
    self.timeout = options.get("timeout", 5)
    self.wordlist_path = options.get("wordlist")
    self.requests = requests

  def fetch(self, *args, **kwargs):
    return self.requests.get(*args, **kwargs)

  def found(self, url, code):
    panel_type = "info"
    if 200 <= code < 300:
      panel_type = "success"
    elif 400 <= code < 500:
      panel_type = "warning"

    console.wg.panel("Found 𖤛", f"{url}", type=panel_type)
    console.hr()

  def check_url(self, base_url, word):
    url = urljoin(base_url, word.strip())
    try:
      response = self.fetch(url, timeout=self.timeout)
      if response.status_code < 400:
        self.found(url, response.status_code)
    except self.requests.RequestException:
      pass

  def end_panel(self):
    console.wg.panel("Completed", "Successfully completed ;)")

  def scan(self):
    if not self.wordlist_path:
      # set default wordlist here
      self.wordlist_path = console.fs.ask_file("Select wordlist")[0]

    self.wordlist_path = Path(self.wordlist_path)
    with open(self.wordlist_path, "r") as f:
      words = f.readlines()

    console.print(f"[green]STARTED[/green] USING [blue]{self.wordlist_path.name}[/blue]", center=True)
    console.br()
    console.hr()

    for word in words:
      self.check_url(self.url, word)
  
    self.end_panel()
    console.hr()

def scan(options: dict):
  console.clear()
  display_banner()
  Pheonix(options).scan()

def start():
  console.br(1)
  scan(intro())

