import os
import sys
import json

from sys import argv
from time import sleep
from pathlib import Path
from random import choice
from importlib import import_module
from subprocess import PIPE

from nekolib import js, panel
from nekolib.process import sh
from nekolib.console import Console
from nekolib.utils import safe_code
from nekolib.ui import Div, Pre, Center, Style, Animate, Text, Padding, Element

from banners import BANNERS

from typing import List, Union

# scripts directory
BASE_DIR = Path(__file__).resolve().parent / "scripts"
#BASE_DIR = Path(os.environ.get("KIKX_HOME_PATH"))

# only scripts with this extension will be in list
SCRIPT_ICONS = {
  "": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path fill="currentColor" d="m13.85 4.44l-3.279-3.301l-.351-.14H2.5l-.5.5v13l.5.5h11l.5-.5V4.8zM13 14H3V2h7l3 3zm-7.063-1.714h.792v.672H4.293v-.672h.798V9.888l-.819.178v-.687l1.665-.336zm3.617-3.278q-.706 0-1.079.526q-.37.524-.371 1.525q0 1.931 1.375 1.932q.684 0 1.05-.522q.368-.521.368-1.498q0-1.964-1.343-1.964zm-.048 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.515 0 .516 1.343q0 1.342-.526 1.343zm.431-5.055h.792v.672H8.293v-.672h.798V4.888l-.819.178v-.688l1.665-.336zM5.554 4.009q-.707 0-1.08.526q-.37.524-.37 1.525q0 1.93 1.375 1.931q.684 0 1.05-.521q.368-.52.368-1.499q0-1.962-1.343-1.962m-.049 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.516 0 .516 1.343t-.527 1.343"/></svg>',
  ".py": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><path fill="#0288d1" d="M9.86 2A2.86 2.86 0 0 0 7 4.86v1.68h4.29c.39 0 .71.57.71.96H4.86A2.86 2.86 0 0 0 2 10.36v3.781a2.86 2.86 0 0 0 2.86 2.86h1.18v-2.68a2.85 2.85 0 0 1 2.85-2.86h5.25c1.58 0 2.86-1.271 2.86-2.851V4.86A2.86 2.86 0 0 0 14.14 2zm-.72 1.61c.4 0 .72.12.72.71s-.32.891-.72.891c-.39 0-.71-.3-.71-.89s.32-.711.71-.711"/><path fill="#fdd835" d="M17.959 7v2.68a2.85 2.85 0 0 1-2.85 2.859H9.86A2.85 2.85 0 0 0 7 15.389v3.75a2.86 2.86 0 0 0 2.86 2.86h4.28A2.86 2.86 0 0 0 17 19.14v-1.68h-4.291c-.39 0-.709-.57-.709-.96h7.14A2.86 2.86 0 0 0 22 13.64V9.86A2.86 2.86 0 0 0 19.14 7zM8.32 11.513l-.004.004l.038-.004zm6.54 7.276c.39 0 .71.3.71.89a.71.71 0 0 1-.71.71c-.4 0-.72-.12-.72-.71s.32-.89.72-.89"/></svg>',
  ".js": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 256 256"><g fill="none"><rect width="256" height="256" fill="#f0db4f" rx="60"/><path fill="#323330" d="m67.312 213.932l19.59-11.856c3.78 6.701 7.218 12.371 15.465 12.371c7.905 0 12.889-3.092 12.889-15.12v-81.798h24.058v82.138c0 24.917-14.606 36.259-35.916 36.259c-19.245 0-30.416-9.967-36.087-21.996m85.07-2.576l19.588-11.341c5.157 8.421 11.859 14.607 23.715 14.607c9.969 0 16.325-4.984 16.325-11.858c0-8.248-6.53-11.17-17.528-15.98l-6.013-2.579c-17.357-7.388-28.871-16.668-28.871-36.258c0-18.044 13.748-31.792 35.229-31.792c15.294 0 26.292 5.328 34.196 19.247l-18.731 12.029c-4.125-7.389-8.591-10.31-15.465-10.31c-7.046 0-11.514 4.468-11.514 10.31c0 7.217 4.468 10.139 14.778 14.608l6.014 2.577c20.449 8.765 31.963 17.699 31.963 37.804c0 21.654-17.012 33.51-39.867 33.51c-22.339 0-36.774-10.654-43.819-24.574"/></g></svg>',
  ".lua": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 32 32"><path fill="#42a5f5" d="M30 6a3.86 3.86 0 0 1-1.167 2.833a4.024 4.024 0 0 1-5.666 0A3.86 3.86 0 0 1 22 6a3.86 3.86 0 0 1 1.167-2.833a4.024 4.024 0 0 1 5.666 0A3.86 3.86 0 0 1 30 6m-9.208 5.208A10.6 10.6 0 0 0 13 8a10.6 10.6 0 0 0-7.792 3.208A10.6 10.6 0 0 0 2 19a10.6 10.6 0 0 0 3.208 7.792A10.6 10.6 0 0 0 13 30a10.6 10.6 0 0 0 7.792-3.208A10.6 10.6 0 0 0 24 19a10.6 10.6 0 0 0-3.208-7.792m-1.959 7.625a4.024 4.024 0 0 1-5.666 0a4.024 4.024 0 0 1 0-5.666a4.024 4.024 0 0 1 5.666 0a4.024 4.024 0 0 1 0 5.666"/></svg>',
  ".txt": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><g fill="none" stroke="#cad3f5" stroke-linecap="round" stroke-linejoin="round" stroke-width="1"><path d="M13.5 6.5v6a2 2 0 0 1-2 2h-7a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h4.01"/><path d="m8.5 1.5l5 5h-4a1 1 0 0 1-1-1zm-3 10h5m-5-3h5m-5-3h1"/></g></svg>',
}

CURRENT_BANNER = BANNERS[0]

def scripts_list(path: Union[str, Path], suffixes: List[str]) -> List[Path]:
  path = Path(path)
  return sorted([
    item for item in path.iterdir()
    if (
      not item.name.startswith("_") and 
      (item.is_dir() or (item.is_file() and item.suffix in suffixes))
    )
  ])

# Returns file icon svg
def get_file_icon(script: Path) -> str:
  if script.is_dir():
    return '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="64" stroke-dashoffset="64" d="M12 7h8c0.55 0 1 0.45 1 1v10c0 0.55 -0.45 1 -1 1h-16c-0.55 0 -1 -0.45 -1 -1v-11Z"><animate fill="freeze" attributeName="fill-opacity" begin="0.8s" dur="0.15s" values="0;0.3"/><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="64;0"/></path><path d="M12 7h-9v0c0 0 0.45 0 1 0h6z" opacity="0"><animate fill="freeze" attributeName="d" begin="0.6s" dur="0.2s" values="M12 7h-9v0c0 0 0.45 0 1 0h6z;M12 7h-9v-1c0 -0.55 0.45 -1 1 -1h6z"/><set fill="freeze" attributeName="opacity" begin="0.6s" to="1"/></path></g></svg>'
  else:
    return SCRIPT_ICONS.get(script.suffix, "<div>🤔</div>")

# require full path for recursive
def list_scripts(scripts_panel: Element, path: Path, directory: str=".") -> None:
  back_icon = f"""
    <div onclick="sendInput('{path.parent}')">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="m4 10l-.707.707L2.586 10l.707-.707zm17 8a1 1 0 1 1-2 0zM8.293 15.707l-5-5l1.414-1.414l5 5zm-5-6.414l5-5l1.414 1.414l-5 5zM4 9h10v2H4zm17 7v2h-2v-2zm-7-7a7 7 0 0 1 7 7h-2a5 5 0 0 0-5-5z"/></svg>
    </div>
  """

  scripts_panel.replace(f"""
    <div class='h-9 p-2 py-3 bg-white text-black flex justify-between items-center'>
      <div>Scripts</div>
      <div class="flex items-center gap-1">
        <div>{directory}</div>
        {"" if directory == "." else back_icon}
      </div>
    </div>
  """)

  scripts_list_div = Div(*[f"""
    <div class='border-b border-gray-400 flex justify-between items-center gap-1 {"bg-gray-500/80" if script.is_dir() else ""}'>
      <div onclick='sendInput("{script}")' class="flex-1 flex gap-1 p-2">
        {get_file_icon(script)}{script.name}
      </div>
      <div style="{'display: none' if script.is_dir() or script.suffix == ".txt" else ''}" onclick='sendInput("__help__ {script}")' class="p-4 w-12"></div>
    </div>
  """ for script in scripts_list(path, SCRIPT_ICONS.keys())])
  scripts_list_div.cls.add_class("flex-1 overflow-y-auto scroll-smooth")
  
  scripts_panel.append(Animate(scripts_list_div))

def random_banner(element: Element, banner=None) -> None:
  global CURRENT_BANNER
  CURRENT_BANNER = banner if banner else choice([i for i in BANNERS if i != CURRENT_BANNER])

  banner_text = Pre(Animate(Text(CURRENT_BANNER)))
  banner_text.cls.add_class("w-full h-full flex items-end justify-center")
  element.replace(banner_text)

def home_screen() -> None:
  panel.clear(True)

  top_box = Div()
  top_box.cls.add_class("bg-purple-400/40 h-[200px] overflow-auto")
  top_box.set_property("onclick", "sendInput('__banner__')")

  scripts_panel = Div()
  scripts_panel.cls.add_class("flex-1 flex flex-col overflow-hidden")
  
  box = Div(top_box, scripts_panel)
  box.cls.add_class("w-full h-full flex flex-col")

  random_banner(top_box, CURRENT_BANNER)
  list_scripts(scripts_panel, BASE_DIR)

  panel.append(box)

  while True:
    text_input = input().strip()
    
    # special commands
    if text_input == "__banner__":
      random_banner(top_box)
      continue
    elif text_input.startswith("__help__"):
      help_path = (BASE_DIR / "_help" / f"{Path(text_input.split()[-1]).relative_to(BASE_DIR)}.txt")
      if help_path.exists() and not help_path.is_dir():
        with open(help_path, "r") as file:
          banner_text = Div(file.read())
          banner_text.cls.add_class("w-full h-full")
          
          top_box.replace(Animate(banner_text))
      else:
          banner_text = Div(f"""No help found for '{help_path.with_suffix("").name}'""")
          banner_text.cls.add_class("w-full h-full text-md flex items-center justify-center")
        
          top_box.replace(Animate(banner_text))
      continue

    # ---- 
    # absolute path to script
    script_path = Path(text_input)
    # finding relative path based on scripts BASE_DIR
    rel_path = script_path.relative_to(BASE_DIR)

    if script_path.is_dir():
      list_scripts(scripts_panel, script_path, str(rel_path))
    elif script_path.exists():
      text = run_script(script_path)
      if text is None:
        break
      top_box.replace(Animate(Text(text)))

# can support absolute files
def run_script(path: Union[str, Path], *args) -> Union[None, str]:
  path = Path(path)
  if path.suffix == ".txt":
    with open(path) as file:
      return file.read()
  
  panel.clear(True)
  js.run_code(f"runningScript = 'neko {path}' ;setScriptName('{path.name}')")

  # both print and event {} works
  js.run_code("setRawOutput()")
  # support for binary file
  if path.suffix == "":
    binary_path = (path).as_posix()

    sh(f"chmod +x {binary_path}").pipe()
    process = sh(binary_path).pipe(stderr=PIPE)
    if process.returncode != 0:
      raise Exception(f"Error: {process.error()}")
  # python file
  elif path.suffix == ".py":
    # adding nekolib 
    sys.path.insert(0, "nekolib")
    # for relative scripts
    try:
      path = path.relative_to(Path(__file__).parent / "scripts")
      
      module = import_module("scripts." + path.with_suffix("").as_posix().replace("/", "."))
      func = getattr(module, "start", None)
      if callable(func):
        func(*args)
    # for absolute scripts
    except Exception:
      with open(path) as file:
        exec(file.read(), { "args": args })
  # lua file
  elif path.suffix == ".lua":
    from lupa import LuaRuntime
  
    runtime = LuaRuntime()
    runtime.globals().console = Console()

    with open(path, "r") as file:
      runtime.execute(file.read())
  # js will run in app
  elif path.suffix == ".js":
    with open(path, "r") as file:
      js.run_code(file.read())
  else:
    raise Exception(f"Cant run '{path.suffix}' file")

def main() -> None:
  js.run_code("blockUserClear()")

  if len(argv) >= 2:
    run_script(argv[1], *argv[2:])
  else:
    home_screen()

if __name__ == "__main__":
  main()
