import os
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
from nekolib.ui import Div, Pre, Center, Style, Animate, Text, Padding


# scripts
BASE_DIR = Path(__file__).resolve().parent / "scripts"

B1 = r"""
♡  /)/)
 （„• ֊ •„)♡              
┏ • UU • - • - • - • - • - • - • ღ❦ღ┓
                 <span class="text-blue-300 font-bold">NEKO</span> 
            created by <span class="text-red-300">kikx</span>
┗ღ❦ღ • - • - • - • - • - • - • - •  ┛
     \(•.•)/              \(•.•)/
       | |                  | |
      _/ \_                _/ \_
/````````````````````````````````````\
"""

B2 = r"""
       /)/) E            K (\(\
      (•.•)/              \(•.•)
     N/| |                  | |\O
      _/ \_                _/ \_
/````````````````````````````````````\
"""


BANNERS = [B1, B2]
CURRENT = B1


def scripts_list(path):
  #return [name.replace(".py", "") for name in sorted(safe_code(os.listdir(BASE_DIR))) if name.endswith(".py") or not name.startswith("__")]
  return sorted([Path(path) / name for name in safe_code(os.listdir(path)) if not name.startswith("_")])

# Returns file icon svg 
def get_file_icon(script):
  # default_icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><path fill="currentColor" d="M14 11a3 3 0 0 1-3-3V4H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-8zm-2-3a2 2 0 0 0 2 2h3.59L12 4.41zM7 3h5l7 7v9a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3"/></svg>'
  default_icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path fill="currentColor" d="m13.85 4.44l-3.279-3.301l-.351-.14H2.5l-.5.5v13l.5.5h11l.5-.5V4.8zM13 14H3V2h7l3 3zm-7.063-1.714h.792v.672H4.293v-.672h.798V9.888l-.819.178v-.687l1.665-.336zm3.617-3.278q-.706 0-1.079.526q-.37.524-.371 1.525q0 1.931 1.375 1.932q.684 0 1.05-.522q.368-.521.368-1.498q0-1.964-1.343-1.964zm-.048 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.515 0 .516 1.343q0 1.342-.526 1.343zm.431-5.055h.792v.672H8.293v-.672h.798V4.888l-.819.178v-.688l1.665-.336zM5.554 4.009q-.707 0-1.08.526q-.37.524-.37 1.525q0 1.93 1.375 1.931q.684 0 1.05-.521q.368-.52.368-1.499q0-1.962-1.343-1.962m-.049 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.516 0 .516 1.343t-.527 1.343"/></svg>'
  icons = {
    "": default_icon,
    ".py": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><path fill="#0288d1" d="M9.86 2A2.86 2.86 0 0 0 7 4.86v1.68h4.29c.39 0 .71.57.71.96H4.86A2.86 2.86 0 0 0 2 10.36v3.781a2.86 2.86 0 0 0 2.86 2.86h1.18v-2.68a2.85 2.85 0 0 1 2.85-2.86h5.25c1.58 0 2.86-1.271 2.86-2.851V4.86A2.86 2.86 0 0 0 14.14 2zm-.72 1.61c.4 0 .72.12.72.71s-.32.891-.72.891c-.39 0-.71-.3-.71-.89s.32-.711.71-.711"/><path fill="#fdd835" d="M17.959 7v2.68a2.85 2.85 0 0 1-2.85 2.859H9.86A2.85 2.85 0 0 0 7 15.389v3.75a2.86 2.86 0 0 0 2.86 2.86h4.28A2.86 2.86 0 0 0 17 19.14v-1.68h-4.291c-.39 0-.709-.57-.709-.96h7.14A2.86 2.86 0 0 0 22 13.64V9.86A2.86 2.86 0 0 0 19.14 7zM8.32 11.513l-.004.004l.038-.004zm6.54 7.276c.39 0 .71.3.71.89a.71.71 0 0 1-.71.71c-.4 0-.72-.12-.72-.71s.32-.89.72-.89"/></svg>',
    ".lua": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 32 32"><path fill="#42a5f5" d="M30 6a3.86 3.86 0 0 1-1.167 2.833a4.024 4.024 0 0 1-5.666 0A3.86 3.86 0 0 1 22 6a3.86 3.86 0 0 1 1.167-2.833a4.024 4.024 0 0 1 5.666 0A3.86 3.86 0 0 1 30 6m-9.208 5.208A10.6 10.6 0 0 0 13 8a10.6 10.6 0 0 0-7.792 3.208A10.6 10.6 0 0 0 2 19a10.6 10.6 0 0 0 3.208 7.792A10.6 10.6 0 0 0 13 30a10.6 10.6 0 0 0 7.792-3.208A10.6 10.6 0 0 0 24 19a10.6 10.6 0 0 0-3.208-7.792m-1.959 7.625a4.024 4.024 0 0 1-5.666 0a4.024 4.024 0 0 1 0-5.666a4.024 4.024 0 0 1 5.666 0a4.024 4.024 0 0 1 0 5.666"/></svg>'
  }
  
  if script.is_dir():
    return '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="64" stroke-dashoffset="64" d="M12 7h8c0.55 0 1 0.45 1 1v10c0 0.55 -0.45 1 -1 1h-16c-0.55 0 -1 -0.45 -1 -1v-11Z"><animate fill="freeze" attributeName="fill-opacity" begin="0.8s" dur="0.15s" values="0;0.3"/><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="64;0"/></path><path d="M12 7h-9v0c0 0 0.45 0 1 0h6z" opacity="0"><animate fill="freeze" attributeName="d" begin="0.6s" dur="0.2s" values="M12 7h-9v0c0 0 0.45 0 1 0h6z;M12 7h-9v-1c0 -0.55 0.45 -1 1 -1h6z"/><set fill="freeze" attributeName="opacity" begin="0.6s" to="1"/></path></g></svg>'
  else:
    return icons.get(script.suffix, default_icon)

# require full path for recursive
def list_scripts(element, path, directory="."):
  div = Div()
  back_icon = f"""
    <div onclick="sendInput('{path.parent}')">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="m4 10l-.707.707L2.586 10l.707-.707zm17 8a1 1 0 1 1-2 0zM8.293 15.707l-5-5l1.414-1.414l5 5zm-5-6.414l5-5l1.414 1.414l-5 5zM4 9h10v2H4zm17 7v2h-2v-2zm-7-7a7 7 0 0 1 7 7h-2a5 5 0 0 0-5-5z"/></svg>
    </div>
  """

  div.append(f"""
    <div class='p-2 bg-white text-black flex justify-between items-center'>
      <div>Scripts</div>
      <div class="flex items-center gap-1">
        <div>{directory}</div>
        {"" if directory == "." else back_icon}
      </div>
    </div>
  """)
  
  div.append(Animate(Div(*[f"""<div class='p-2 border-b flex items-center gap-1 {"bg-gray-500/80" if script.is_dir() else ""}' onclick='sendInput("{script}")'>{get_file_icon(script)}{script.name}</div>""" for script in scripts_list(path)])))
  div.cls.add_class("w-full *:text-sm")
  
  element.replace(div)

def random_banner(element):
  banner = choice([i for i in BANNERS if i != CURRENT])
  global CURRENT
  CURRENT = banner
  element.replace(Animate(Text(banner)))

def home_screen():
  panel.clear(True)
  banner = Pre(Animate(Text(CURRENT)))
  banner.cls.add_class("flex justify-center items-end bg-purple-400/40 min-h-[200px]")
  
  banner.set_property("onclick", "sendInput('__banner__')")

  panel.append(banner)
  
  scripts_panel = Div()
  list_scripts(scripts_panel, BASE_DIR)
  panel.append(scripts_panel)
  
  while True:
    text_input = input().strip()
    if text_input == "__banner__":
      random_banner(banner)
      continue
    # ----
    script_path = Path(text_input)
    rel_path = script_path.relative_to(BASE_DIR)
  
    if script_path.is_dir():
      list_scripts(scripts_panel, script_path, str(rel_path))
    elif script_path.exists():
      js.run_code(f"runningScript = 'neko {rel_path}' ;setScriptName('{script_path.name}')")
      return run_script(rel_path)
  #if script_path.exists() and script_path.suffix == ".py":
    #run_script(script_path.name)

# TODO: add support for absolute files
def run_script(path, *args):
  panel.clear(True)
  
  path = Path(path)

  # support for binary file
  if path.suffix == "":
    # both print and event {} works
    js.run_code("setRawOutput()")
    
    binary_path = (BASE_DIR / path).as_posix()

    sh(f"chmod +x {binary_path}").pipe()
    process = sh(binary_path).pipe(stderr=PIPE)
    if process.returncode != 0:
      raise Exception(f"Error: {process.error()}")
  # python file
  elif path.suffix == ".py":
    module = import_module("scripts." + path.with_suffix("").as_posix().replace("/", "."))
  
    func = getattr(module, "start", None)
    if callable(func):
      func(*args)
  # lua file
  elif path.suffix == ".lua":
    from lupa import LuaRuntime
  
    runtime = LuaRuntime()
    runtime.globals().console = Console()

    with open(BASE_DIR / path, "r") as file:
      runtime.execute(file.read())
  else:
    raise Exception(f"Cant run '{path.suffix}' file")

def main():
  js.run_code("blockUserClear()")

  if len(argv) >= 2:
    run_script(argv[1], *argv[2:])
  else:
    home_screen()
  
if __name__ == "__main__":
  main()

# neko
# neko <name> <args>
