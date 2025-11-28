import os
import sys
import json
import shlex

import importlib.util

from sys import argv
from time import sleep
from pathlib import Path
from random import choice
from importlib import import_module, reload
from subprocess import PIPE

from neko import js, panel
from neko.console import Console
from neko.banners import BANNERS
from neko.ui import Div, Pre, Center, Animate, Text, Padding, Element
from neko.lib.utils import clean
from neko.lib.process import sh
from neko.app import JApp

from typing import List, Union

def ensure_dir(path: str) -> str:
  Path(path).mkdir(parents=True, exist_ok=True)
  return path

ROOT_PATH = Path(__file__).resolve().parent
# scripts directory
SCRIPT_DIRS = [
  ("App", ensure_dir(ROOT_PATH / "etc/nks")),
  ("Local", ensure_dir(Path(os.environ.get("KIKX_HOME_PATH", ROOT_PATH / "etc/.empty")) / "etc/nks"))
]

SCRIPTS_DIR_NAME, SCRIPTS_DIR = SCRIPT_DIRS[0]

# only scripts with this extension will be in list
SCRIPT_ICONS = {
  "": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path fill="currentColor" d="m13.85 4.44l-3.279-3.301l-.351-.14H2.5l-.5.5v13l.5.5h11l.5-.5V4.8zM13 14H3V2h7l3 3zm-7.063-1.714h.792v.672H4.293v-.672h.798V9.888l-.819.178v-.687l1.665-.336zm3.617-3.278q-.706 0-1.079.526q-.37.524-.371 1.525q0 1.931 1.375 1.932q.684 0 1.05-.522q.368-.521.368-1.498q0-1.964-1.343-1.964zm-.048 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.515 0 .516 1.343q0 1.342-.526 1.343zm.431-5.055h.792v.672H8.293v-.672h.798V4.888l-.819.178v-.688l1.665-.336zM5.554 4.009q-.707 0-1.08.526q-.37.524-.37 1.525q0 1.93 1.375 1.931q.684 0 1.05-.521q.368-.52.368-1.499q0-1.962-1.343-1.962m-.049 3.333q-.54 0-.54-1.303q0-1.383.551-1.383q.516 0 .516 1.343t-.527 1.343"/></svg>',
  ".sh": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path fill="#d9b400" d="M29.4 27.6H2.5V4.5h26.9Zm-25.9-1h24.9V5.5H3.5Z"/><path fill="#d9b400" d="m6.077 19.316l-.555-.832l4.844-3.229l-4.887-4.071l.641-.768l5.915 4.928zM12.7 18.2h7.8v1h-7.8zM2.5 5.5h26.9v1.9H2.5z"/></svg>',
  ".py": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#0288d1" d="M9.86 2A2.86 2.86 0 0 0 7 4.86v1.68h4.29c.39 0 .71.57.71.96H4.86A2.86 2.86 0 0 0 2 10.36v3.781a2.86 2.86 0 0 0 2.86 2.86h1.18v-2.68a2.85 2.85 0 0 1 2.85-2.86h5.25c1.58 0 2.86-1.271 2.86-2.851V4.86A2.86 2.86 0 0 0 14.14 2zm-.72 1.61c.4 0 .72.12.72.71s-.32.891-.72.891c-.39 0-.71-.3-.71-.89s.32-.711.71-.711"/><path fill="#fdd835" d="M17.959 7v2.68a2.85 2.85 0 0 1-2.85 2.859H9.86A2.85 2.85 0 0 0 7 15.389v3.75a2.86 2.86 0 0 0 2.86 2.86h4.28A2.86 2.86 0 0 0 17 19.14v-1.68h-4.291c-.39 0-.709-.57-.709-.96h7.14A2.86 2.86 0 0 0 22 13.64V9.86A2.86 2.86 0 0 0 19.14 7zM8.32 11.513l-.004.004l.038-.004zm6.54 7.276c.39 0 .71.3.71.89a.71.71 0 0 1-.71.71c-.4 0-.72-.12-.72-.71s.32-.89.72-.89"/></svg>',
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

    sh(f"chmod +x {binary_path}").run()
    process = sh(binary_path).pipe(stderr=PIPE)
    if process.returncode != 0:
      print(f"Error({process.returncode}): {process.error()}")
  elif path.suffix == ".sh":
    # can parse html code
    script_path = (path).as_posix()

    process = sh(f"bash {script_path}").pipe(stderr=PIPE)
    if process.returncode != 0:
      print(f"Error({process.returncode}): {process.error()}")
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


class Neko(JApp):
  def init(self) -> None:
    self.current_banner = BANNERS[0] # default banner
    self.current_dir = SCRIPTS_DIR # start directory
    
    self.current_script = "neko"

    self.last_saves = {} # tracking script switch path
  
  def list_scripts(self, path: Path, directory: str=".") -> None:
    def create_dir_name(name):
      return f"""
        <div class="border-b" {self.on("run", Utils.get_path_up_to_suffix(path, name))}>{clean(name.replace('/', ' > '))}</div>
      """
  
    right_text = "" if directory == "." else " > ".join([create_dir_name(name) for name in directory.split("/")]) + f"""
      <div {self.on("run", path.parent)}>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="m4 10l-.707.707L2.586 10l.707-.707zm17 8a1 1 0 1 1-2 0zM8.293 15.707l-5-5l1.414-1.414l5 5zm-5-6.414l5-5l1.414 1.414l-5 5zM4 9h10v2H4zm17 7v2h-2v-2zm-7-7a7 7 0 0 1 7 7h-2a5 5 0 0 0-5-5z"/></svg>
      </div>
    """
  
    self.scripts_panel.replace(f"""
      <div class='h-9 p-1 py-3 bg-gradient-to-r border-2 border-white/80 from-pink-400/80 to-blue-400/80 text-black flex gap-2 justify-between items-center'>
        <div class="flex items-center gap-1" onclick="sendInput('$next')">
          <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14.293 2.293a1 1 0 0 1 1.414 0l4 4a1 1 0 0 1 0 1.414l-4 4a1 1 0 0 1-1.414-1.414L16.586 8H5a1 1 0 0 1 0-2h11.586l-2.293-2.293a1 1 0 0 1 0-1.414m-4.586 10a1 1 0 0 1 0 1.414L7.414 16H19a1 1 0 1 1 0 2H7.414l2.293 2.293a1 1 0 0 1-1.414 1.414l-4-4a1 1 0 0 1 0-1.414l4-4a1 1 0 0 1 1.414 0"/></svg>
          <div class="font-bold text-md">{clean(SCRIPTS_DIR_NAME)}</div>
        </div>
        <div class="flex items-center gap-1 overflow-y-auto">
          {right_text}
        </div>
      </div>
    """)

    scripts_list_div = Div(*[f"""
      <div class='border-b border-gray-400 flex justify-between items-center gap-1 {"bg-gray-400/40" if script.is_dir() else ""}'>
        <div {self.on("run", script)} class="flex-1 flex items-center gap-1.5 p-2">
          <div class="w-4 h-4 overflow-hidden">{get_file_icon(script)}</div>
          <div>{clean(script.with_suffix("").name)}</div>
        </div>
        <div style="{'display: none' if script.is_dir() or script.suffix == ".txt" else ''}" {self.on("help", script)} class="p-4 w-12"></div>
      </div>
    """ for script in scripts_list(path, SCRIPT_ICONS.keys())])
    scripts_list_div.add_class("flex-1 overflow-y-auto scroll-smooth")
    
    self.scripts_panel.append(Animate(scripts_list_div))

  def set_next_scripts(self) -> None:
    self.last_saves[SCRIPTS_DIR_NAME] = self.current_dir
    set_next_scripts_path()

    self.current_dir = self.last_saves.get(SCRIPTS_DIR_NAME, SCRIPTS_DIR)

  def create_home_screen(self) -> None:
    self.top_box = Div()
    self.top_box.add_class("bg-purple-400/40 h-[220px] landscape:h-full landscape:flex-1 overflow-y-auto")
    self.top_box.set_property("onclick", self.send("$banner"))

    self.scripts_panel = Div()
    self.scripts_panel.add_class("flex-1 flex flex-col landscape:bg-purple-400/40 landscape:flex-1 overflow-hidden")
  
    landscape_divider = Div()
    landscape_divider.add_class("hidden landscape:block w-[2px] bg-white")
  
    self.box = Div(self.top_box, landscape_divider, self.scripts_panel)
    self.box.add_class("w-full h-full flex flex-col landscape:flex-row")

    self.random_banner(self.current_banner)

    #panel.clear(True)
    panel.inject(self.box)
    
    # resets to neko on home screen
    js.run_code("runningScript = 'neko'; setSubTaskName()")

  def create_end_buttons(self) -> None:
    panel.append(Animate(Div("""
      <div class="absolute flex z-[800] bottom-2 right-2 p-3 rounded space-x-1">
        <!-- Run Button -->
        <div onclick="sendInput('$rerun')" class="bg-green-400/80 p-2 rounded cursor-pointer transition">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-white" viewBox="0 0 16 16"><g fill="currentColor"><path d="M2.78 2L2 2.41v12l.78.42l9-6V8zM3 13.48V3.35l7.6 5.07z"/><path fill-rule="evenodd" d="m6 14.683l8.78-5.853V8L6 2.147V3.35l7.6 5.07L6 13.48z" clip-rule="evenodd"/></g></svg>
        </div>
      
        <!-- Home Button -->
        <div onclick="sendInput('$home')" class="bg-red-400/80 p-2 rounded cursor-pointer transition">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M12 15l3-3-3-3m3 3H4M4 10.248V7.2c0-1.12 0-1.68.218-2.108a2 2 0 01.874-.874C5.52 4 6.08 4 7.2 4h9.6c1.12 0 1.68 0 2.107.218.377.192.683.497.875.874.218.427.218.987.218 2.105v9.607c0 1.118 0 1.677-.218 2.104a2 2 0 01-.875.874c-.427.218-.986.218-2.104.218H7.197c-1.118 0-1.678 0-2.105-.218a2 2 0 01-.874-.874C4 18.48 4 17.92 4 16.8v-.05" /></svg>
        </div>
      </div>
    """)))

  def random_banner(self, banner=None) -> None:
    self.current_banner = banner if banner else choice([i for i in BANNERS if i != self.current_banner])
  
    banner_text = Div(self.current_banner)
    banner_text.add_class("w-full h-full")
    
    self.top_box.replace(banner_text)
  
  def display_scripts(self, current_dir=None, rel_path=None) -> None:
    self.list_scripts(current_dir or self.current_dir, rel_path or str(self.current_dir.relative_to(SCRIPTS_DIR)))

  # events
  def default(self, command):
    if command == "$banner":
      self.random_banner()
    elif command == "$next":
      self.set_next_scripts()
      self.display_scripts()
    elif command == "$home":
      self.create_home_screen()
      self.display_scripts()
    elif command == "$rerun":
      self.run_script(self.current_script)

  def on_help(self, path):
    path = Path(path)

    help_file_path = path.parent / f"_{path.name}.txt"
  
    if help_file_path.exists() and not help_file_path.is_dir():
      banner_text = Div(help_file_path.read_text(encoding="utf-8"))
      banner_text.add_class("w-full h-full")
          
      self.top_box.replace(Animate(banner_text))
    else:
      banner_text = Div(f"""No help found for '{path.with_suffix("").name}'""")
      banner_text.add_class("w-full h-full text-md flex items-center justify-center")
      self.top_box.replace(Animate(banner_text))

  def on_run(self, path):
    script_path = Path(path)
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

  def run_script(self, script_name, *args):
    script_name = Path(script_name)
    self.current_script = script_name
    
    # clearing panel
    panel.clear(True)
    js.run_code(f"""runningScript = 'neko "{clean(str(script_name))}"' ;setSubTaskName('{script_name.name}')""")

    run_script(script_name, *args)
  
    # setting default after complete and hiding input
    js.set_default_config()
    js.hide_input_panel()

    self.create_end_buttons()

  def main(self, script_name=None, *args):
    # if started with script name
    if script_name:
      self.run_script(script_name, *args)
    else:
      self.create_home_screen()
      self.display_scripts(self.current_dir, ".")

    self.startloop()

if __name__ == "__main__":
  Neko().main(*argv[1:])
