from sys import argv
from nekolib import js, panel

from nekolib.process import sh
from nekolib.ui import Pre, Center, Style, Animate, Text, Padding
from nekolib.utils import safe_code

import json
from time import sleep
from importlib import import_module

from nekolib.ui import Div
import os
from pathlib import Path

from random import choice

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
  
  div.append(Animate(Div(*[f"""<div class='p-2 border-b {"bg-gray-500/80" if script.is_dir() else ""}' onclick='sendInput("{script}")'>{script.name}</div>""" for script in scripts_list(path)])))
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

def run_script(path, *args):
  panel.clear(True)
  
  path = Path(path)
  if path.suffix == ".py":
    module = import_module("scripts." + path.with_suffix("").as_posix().replace("/", "."))
  
    func = getattr(module, "start", None)
    if callable(func):
      func(*args)
  else:
    raise Exception(f"Cant run {path.suffix} file")
  
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
