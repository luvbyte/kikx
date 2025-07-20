import os
import sys
import json

import importlib.util

from sys import argv
from time import sleep
from pathlib import Path
from random import choice
from importlib import import_module, reload
from subprocess import PIPE

from neko.lib import js, panel
from neko.lib.process import sh
from neko.lib.console import Console
from neko.lib.utils import safe_code
from neko.lib.ui import Div, Pre, Center, Style, Animate, Text, Padding, Element

from neko.banners import BANNERS

from typing import List, Union


NEKO_PATH = Path(__file__).resolve().parent / "neko"
# scripts directory
SCRIPT_DIRS = [
  ("App", NEKO_PATH / "scripts"),
  ("Local", Path(os.environ.get("KIKX_HOME_PATH")) / "dev/neko_scripts")
]

SCRIPTS_DIR_NAME, SCRIPTS_DIR = SCRIPT_DIRS[0]

# only scripts with this extension will be in list
SCRIPT_ICONS = {
  "": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path fill="currentColor" d="m13.85 4.44l-3.279-3.301l-.351-.14H2.5l-.5.5v13l.5.5h11l.5-.5V4.8zM13 14H3V2h7l3 3zm-7.063-1.714h.792v.672H4.293v-.672h.798V9.888l-.819.178v-.687l1.665-.336zm3.617-3.278q-.706 0-1.079.526q-.37.524-.371 1.525q0 1.931 1.375 1.932q.684 0 1.05-.522q.368-.521.368-1.498q0-1.964-1.343-1.964zm-.048 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.515 0 .516 1.343q0 1.342-.526 1.343zm.431-5.055h.792v.672H8.293v-.672h.798V4.888l-.819.178v-.688l1.665-.336zM5.554 4.009q-.707 0-1.08.526q-.37.524-.37 1.525q0 1.93 1.375 1.931q.684 0 1.05-.521q.368-.52.368-1.499q0-1.962-1.343-1.962m-.049 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.516 0 .516 1.343t-.527 1.343"/></svg>',
  ".py": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#0288d1" d="M9.86 2A2.86 2.86 0 0 0 7 4.86v1.68h4.29c.39 0 .71.57.71.96H4.86A2.86 2.86 0 0 0 2 10.36v3.781a2.86 2.86 0 0 0 2.86 2.86h1.18v-2.68a2.85 2.85 0 0 1 2.85-2.86h5.25c1.58 0 2.86-1.271 2.86-2.851V4.86A2.86 2.86 0 0 0 14.14 2zm-.72 1.61c.4 0 .72.12.72.71s-.32.891-.72.891c-.39 0-.71-.3-.71-.89s.32-.711.71-.711"/><path fill="#fdd835" d="M17.959 7v2.68a2.85 2.85 0 0 1-2.85 2.859H9.86A2.85 2.85 0 0 0 7 15.389v3.75a2.86 2.86 0 0 0 2.86 2.86h4.28A2.86 2.86 0 0 0 17 19.14v-1.68h-4.291c-.39 0-.709-.57-.709-.96h7.14A2.86 2.86 0 0 0 22 13.64V9.86A2.86 2.86 0 0 0 19.14 7zM8.32 11.513l-.004.004l.038-.004zm6.54 7.276c.39 0 .71.3.71.89a.71.71 0 0 1-.71.71c-.4 0-.72-.12-.72-.71s.32-.89.72-.89"/></svg>',
  ".js": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><g fill="none"><rect width="256" height="256" fill="#f0db4f" rx="60"/><path fill="#323330" d="m67.312 213.932l19.59-11.856c3.78 6.701 7.218 12.371 15.465 12.371c7.905 0 12.889-3.092 12.889-15.12v-81.798h24.058v82.138c0 24.917-14.606 36.259-35.916 36.259c-19.245 0-30.416-9.967-36.087-21.996m85.07-2.576l19.588-11.341c5.157 8.421 11.859 14.607 23.715 14.607c9.969 0 16.325-4.984 16.325-11.858c0-8.248-6.53-11.17-17.528-15.98l-6.013-2.579c-17.357-7.388-28.871-16.668-28.871-36.258c0-18.044 13.748-31.792 35.229-31.792c15.294 0 26.292 5.328 34.196 19.247l-18.731 12.029c-4.125-7.389-8.591-10.31-15.465-10.31c-7.046 0-11.514 4.468-11.514 10.31c0 7.217 4.468 10.139 14.778 14.608l6.014 2.577c20.449 8.765 31.963 17.699 31.963 37.804c0 21.654-17.012 33.51-39.867 33.51c-22.339 0-36.774-10.654-43.819-24.574"/></g></svg>',
  ".lua": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path fill="#42a5f5" d="M30 6a3.86 3.86 0 0 1-1.167 2.833a4.024 4.024 0 0 1-5.666 0A3.86 3.86 0 0 1 22 6a3.86 3.86 0 0 1 1.167-2.833a4.024 4.024 0 0 1 5.666 0A3.86 3.86 0 0 1 30 6m-9.208 5.208A10.6 10.6 0 0 0 13 8a10.6 10.6 0 0 0-7.792 3.208A10.6 10.6 0 0 0 2 19a10.6 10.6 0 0 0 3.208 7.792A10.6 10.6 0 0 0 13 30a10.6 10.6 0 0 0 7.792-3.208A10.6 10.6 0 0 0 24 19a10.6 10.6 0 0 0-3.208-7.792m-1.959 7.625a4.024 4.024 0 0 1-5.666 0a4.024 4.024 0 0 1 0-5.666a4.024 4.024 0 0 1 5.666 0a4.024 4.024 0 0 1 0 5.666"/></svg>',
  ".txt": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><g fill="none" stroke="#cad3f5" stroke-linecap="round" stroke-linejoin="round" stroke-width="1"><path d="M13.5 6.5v6a2 2 0 0 1-2 2h-7a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h4.01"/><path d="m8.5 1.5l5 5h-4a1 1 0 0 1-1-1zm-3 10h5m-5-3h5m-5-3h1"/></g></svg>',
}

DIR_ICONS = {
  "docs": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><g fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="#cad3f5" d="m1.875 8l.686-2.743a1 1 0 0 1 .97-.757h10.938a1 1 0 0 1 .97 1.243l-.315 1.26M6 13.5H2.004A1.5 1.5 0 0 1 .5 12V3.5a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v1" stroke-width="1"/><path stroke="#8aadf4" d="M8.5 14.5v-5a1 1 0 0 1 1-1h6v6m-6-1h6v2h-6a1 1 0 1 1 0-2" stroke-width="1"/></g></svg>'
}

class Utils:
  @staticmethod
  def get_path_up_to_suffix(full_path: Path, target_suffix: str) -> Path:
    full_parts = full_path.parts
    target_parts = Path(target_suffix).parts
    target_len = len(target_parts)

    for i in range(len(full_parts) - target_len + 1):
        if full_parts[i:i + target_len] == target_parts:
            return Path(*full_parts[:i + target_len])
    
    raise ValueError(f"Suffix '{target_suffix}' not found in path '{full_path}'")

# can support absolute files
def run_script(path: Path, *args) -> Union[None, str]:
  # support for binary file
  if path.suffix == "":
    binary_path = (path).as_posix()

    sh(f"chmod +x {binary_path}").pipe()
    process = sh(binary_path).pipe(stderr=PIPE)
    if process.returncode != 0:
      raise Exception(f"Error: {process.error()}")
  # python file
  elif path.suffix == ".py":
    spec = importlib.util.spec_from_file_location("script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    func = getattr(module, "start", None)
    if callable(func):
      func(*args)
  # lua file simple 
  elif path.suffix == ".lua":
    from lupa import LuaRuntime
    from neko import neko_module
    
    #module_name = "neko.neko_module"
    #if "neko.neko_module" in sys.modules:
      #module = reload(sys.modules[module_name])
    #else:
      #module = import_module(module_name)

    runtime = LuaRuntime()
    runtime.globals().neko = neko_module

    with open(path, "r") as file:
      runtime.execute(file.read())
  else:
    raise Exception(f"Cant run '{path.suffix}' file")

def set_next_scripts_path():
  global SCRIPTS_DIR
  global SCRIPTS_DIR_NAME

  try:
    current_index = next(
      i for i, (_, path) in enumerate(SCRIPT_DIRS) if path == SCRIPTS_DIR
    )
    next_index = (current_index + 1) % len(SCRIPT_DIRS)
    SCRIPTS_DIR_NAME, SCRIPTS_DIR = SCRIPT_DIRS[next_index]
  except StopIteration:
    # SCRIPTS_DIR not found in SCRIPT_DIRS
    SCRIPTS_DIR_NAME, SCRIPTS_DIR = SCRIPT_DIRS[0]

# Returns file icon svg
def get_file_icon(script: Path) -> str:
  if script.is_dir():
    icon_path = script / "neko-icon.svg"
    if icon_path.exists():
      return icon_path.read_text(encoding="utf-8")
    return DIR_ICONS.get(script.name, '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="64" stroke-dashoffset="64" d="M12 7h8c0.55 0 1 0.45 1 1v10c0 0.55 -0.45 1 -1 1h-16c-0.55 0 -1 -0.45 -1 -1v-11Z"><animate fill="freeze" attributeName="fill-opacity" begin="0.8s" dur="0.15s" values="0;0.3"/><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="64;0"/></path><path d="M12 7h-9v0c0 0 0.45 0 1 0h6z" opacity="0"><animate fill="freeze" attributeName="d" begin="0.6s" dur="0.2s" values="M12 7h-9v0c0 0 0.45 0 1 0h6z;M12 7h-9v-1c0 -0.55 0.45 -1 1 -1h6z"/><set fill="freeze" attributeName="opacity" begin="0.6s" to="1"/></path></g></svg>')
  else:
    return SCRIPT_ICONS.get(script.suffix, "<div>🤔</div>")

def scripts_list(path: Union[str, Path], suffixes: List[str]) -> List[Path]:
  path = Path(path)
  if not path.exists() or not path.is_dir():
    return []

  return sorted([
    item for item in path.iterdir()
    if (
      not item.name.startswith("_") and 
      (item.is_dir() or (item.is_file() and item.suffix in suffixes))
    )
  ])

def list_scripts(scripts_panel: Element, path: Path, directory: str=".") -> None:
  def create_dir_name(name):
    return f"""
      <div class="border-b" onclick="sendInput('$run {Utils.get_path_up_to_suffix(path, name)}')">{name.replace('/', ' > ')}</div>
    """

  right_text = "" if directory == "." else " > ".join([create_dir_name(name) for name in directory.split("/")]) + f"""
    <div onclick="sendInput('$run {path.parent}')">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="m4 10l-.707.707L2.586 10l.707-.707zm17 8a1 1 0 1 1-2 0zM8.293 15.707l-5-5l1.414-1.414l5 5zm-5-6.414l5-5l1.414 1.414l-5 5zM4 9h10v2H4zm17 7v2h-2v-2zm-7-7a7 7 0 0 1 7 7h-2a5 5 0 0 0-5-5z"/></svg>
    </div>
  """

  scripts_panel.replace(f"""
    <div class='h-9 p-1 py-3 bg-gradient-to-r border-2 border-white/80 from-pink-400/80 to-blue-400/80 text-black flex gap-2 justify-between items-center'>
      <div class="flex items-center gap-1" onclick="sendInput('$next')">
        <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14.293 2.293a1 1 0 0 1 1.414 0l4 4a1 1 0 0 1 0 1.414l-4 4a1 1 0 0 1-1.414-1.414L16.586 8H5a1 1 0 0 1 0-2h11.586l-2.293-2.293a1 1 0 0 1 0-1.414m-4.586 10a1 1 0 0 1 0 1.414L7.414 16H19a1 1 0 1 1 0 2H7.414l2.293 2.293a1 1 0 0 1-1.414 1.414l-4-4a1 1 0 0 1 0-1.414l4-4a1 1 0 0 1 1.414 0"/></svg>
        <div class="font-bold text-md">{SCRIPTS_DIR_NAME}</div>
      </div>
      <div class="flex items-center gap-1 overflow-y-auto">
        {right_text}
      </div>
    </div>
  """)

  scripts_list_div = Div(*[f"""
    <div class='border-b border-gray-400 flex justify-between items-center gap-1 {"bg-gray-400/40" if script.is_dir() else ""}'>
      <div onclick='sendInput("$run {script}")' class="flex-1 flex items-center gap-1.5 p-2">
        <div class="w-4 h-4 overflow-hidden">{get_file_icon(script)}</div>
        <div>{script.with_suffix("").name}</div>
      </div>
      <div style="{'display: none' if script.is_dir() or script.suffix == ".txt" else ''}" onclick='sendInput("$help {script}")' class="p-4 w-12"></div>
    </div>
  """ for script in scripts_list(path, SCRIPT_ICONS.keys())])
  scripts_list_div.cls.add_class("flex-1 overflow-y-auto scroll-smooth")
  
  scripts_panel.append(Animate(scripts_list_div))

class Neko:
  def __init__(self) -> None:
    self.current_banner = BANNERS[0] # default banner
    self.current_dir = SCRIPTS_DIR # start directory
    
    self.last_saves = {} # tracking script switch path

  def set_next_scripts(self) -> None:
    self.last_saves[SCRIPTS_DIR_NAME] = self.current_dir
    set_next_scripts_path()

    self.current_dir = self.last_saves.get(SCRIPTS_DIR_NAME, SCRIPTS_DIR)

  def create_home_screen(self) -> None:
    self.top_box = Div()
    self.top_box.cls.add_class("bg-purple-400/40 h-[220px] landscape:h-full landscape:flex-1 overflow-y-auto")
    self.top_box.set_property("onclick", "sendInput('$banner')")
  
    self.scripts_panel = Div()
    self.scripts_panel.cls.add_class("flex-1 flex flex-col landscape:bg-purple-400/40 landscape:flex-1 overflow-hidden")
  
    landscape_divider = Div()
    landscape_divider.cls.add_class("hidden landscape:block w-[2px] bg-white")
  
    self.box = Div(self.top_box, landscape_divider, self.scripts_panel)
    self.box.cls.add_class("w-full h-full flex flex-col landscape:flex-row")
  
    self.random_banner(self.current_banner)

    #panel.clear(True)
    panel.inject(self.box)
    
    # resets to neko on home screen
    js.run_code("runningScript = 'neko'; setSubTaskName()")

  def create_home_button(self) -> None:
    panel.append("""
      <div onclick="sendInput('$home')" class="absolute z-[800] bottom-6 right-6 bg-purple-400/40 p-3 rounded-full">
        <div class="w-6 h-6">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m12 15l3-3m0 0l-3-3m3 3H4m0-4.752V7.2c0-1.12 0-1.68.218-2.108c.192-.377.497-.682.874-.874C5.52 4 6.08 4 7.2 4h9.6c1.12 0 1.68 0 2.107.218c.377.192.683.497.875.874c.218.427.218.987.218 2.105v9.607c0 1.118 0 1.677-.218 2.104a2 2 0 0 1-.875.874c-.427.218-.986.218-2.104.218H7.197c-1.118 0-1.678 0-2.105-.218a2 2 0 0 1-.874-.874C4 18.48 4 17.92 4 16.8v-.05"/></svg>
        </div>
      <div>
    """)

  def random_banner(self, banner=None) -> None:
    self.current_banner = banner if banner else choice([i for i in BANNERS if i != self.current_banner])
  
    banner_text = Div(self.current_banner)
    banner_text.cls.add_class("w-full h-full")
    
    self.top_box.replace(banner_text)
  
  def display_scripts(self, current_dir=None, rel_path=None) -> None:
    list_scripts(self.scripts_panel, current_dir or self.current_dir, rel_path or str(self.current_dir.relative_to(SCRIPTS_DIR)))

  def run_command(self, command: str):
    if command == "$banner":
      self.random_banner()
    elif command == "$next":
      self.set_next_scripts()
      self.display_scripts()
    elif command.startswith("$help"):
      help_path = (SCRIPTS_DIR / "_help" / f"{Path(command.split()[-1]).relative_to(SCRIPTS_DIR)}.txt")
      
      if help_path.exists() and not help_path.is_dir():
        banner_text = Div(help_path.read_text(encoding="utf-8"))
        banner_text.cls.add_class("w-full h-full")
          
        self.top_box.replace(Animate(banner_text))
      else:
        banner_text = Div(f"""No help found for '{help_path.with_suffix("").name}'""")
        banner_text.cls.add_class("w-full h-full text-md flex items-center justify-center")
        
        self.top_box.replace(Animate(banner_text))
    elif command.startswith("$run"):
      # absolute path to script
      script_path = Path(command.split()[-1])
      # finding relative path based on scripts SCRIPTS_DIR
      rel_path = script_path.relative_to(SCRIPTS_DIR)
  
      if script_path.is_dir():
        self.current_dir = script_path
        self.display_scripts(script_path, str(rel_path))
      elif script_path.exists():
        if script_path.suffix == ".txt":
          self.top_box.replace(Animate(Text(script_path.read_text(encoding="utf-8"))))
          self.top_box.scroll_to_top()
        else:
          self.run_script(script_path)

    elif command == "$home":
      return "display-home"

  def run(self):
    self.create_home_screen()
    self.display_scripts(self.current_dir, ".")

    while True:
      result = self.run_command(input().strip())
      if result == "display-home":
        self.create_home_screen()
        self.display_scripts()
  
  def run_script(self, script_name, *args):
    script_name = Path(script_name)
    
    # clearing panel
    panel.clear(True)
    js.run_code(f"runningScript = 'neko {script_name}' ;setSubTaskName('{script_name.name}')")

    run_script(script_name, *args)
    self.create_home_button()
  
    # setting default after complete and hiding input
    js.set_default_config()
    js.hide_input_panel()

  def main(self, script_name=None, *args):
    # if started withoit home screen
    if script_name:
      self.run_script(script_name, *args)
      # no need for checking good for now
      if input().strip() != "$home":
        return

    self.run()

if __name__ == "__main__":
  Neko().main(*argv[1:])
