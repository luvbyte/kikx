from . import adb

from nekolib.console import Console
from nekolib.ui import Animate, Div, Text, Center, Padding

from nekolib.utils import safe_code

from time import sleep
from pathlib import Path

from os import environ
import os
import json


def load_file(path):
  with open(path, "r") as file:
    return file.read()

def ensure_dir(path):
  """Ensure the directory exists. If not, create it."""
  Path(path).mkdir(parents=True, exist_ok=True)
  return path

BASE_DIR = Path(__file__).resolve().parent # cuteadb
STORAGE = ensure_dir(Path(environ.get("KIKX_HOME_PATH", None)) / "Documents/cuteadb")


console = Console()



def print_devices(active_devices):
  console.clear()
  console.append("<div class='p-1 bg-blue-500/60 text-center'>SELECT DEVICE</div>")

  for index, device in enumerate(active_devices):
    console.append(Animate(Div(f"""
      <div class="p-1 border-y bg-purple-400/20 active:bg-blue-400/60" onclick="sendInput('{index}')">
        <div class="flex gap-2">
          <div>{device.manufacturer}</div>
          <div>{device.model}</div>
        </div>
        <div class="*:pl-6">
          <div>State: {device.state}</div>
          <div>SDK Version: {device.sdk_version}</div>
          <div>Android Version: {device.android_version}</div>
          <div>Serial: {device.serial}</div>
        </div>
      </div>
    """)))

def get_device():
  console.pre_center("listening for devices", wait=0)
  while True:
    active_devices = adb.list_active_devices()
    if len(active_devices) > 0:
      print_devices(active_devices)
      return active_devices[int(input())]
    else:
      sleep(1)

def print_line(line, func=None, title="👉", success="😍", error="🥲"):
  title = Text(title)
  text = Text(line)

  status = Div("<div class='animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full'></div>")
  
  if callable(func):
    div = Div(title, text, status)
  else:
    div = Div(text)

  div.cls.add_class("flex gap-1 items-center p-1 *:text-[1rem]")
  console.append(Animate(div))

  if callable(func):
    try:
      func()
      status.replace(Text(success))
    except Exception:
      status.replace(Text(error))

  console.scroll_to_bottom()

def run_script(device, scripts_path, script_name):
  console.clear()
  console.append(f"""
    <div class='p-2 bg-blue-500/60 flex items-center justify-between'>
      <div>{device.manufacturer} {device.model}</div>
      <div>{script_name}</div>
    </div>
  """)
  # content
  with open(scripts_path / script_name) as file:
    exec(file.read(), {
      "device": device,
      "console": console,
      "STORAGE": STORAGE,
      "print_line": print_line
    })

def get_script_name(scripts_meta, name):
  name = name.replace(".cdb", "")
  return safe_code(scripts_meta.get(name, name))

def main(scripts_path):
  scripts_path = Path(scripts_path)
  scripts_meta = json.loads(load_file(scripts_path / "meta.json"))

  device = get_device()

  console.clear()
  console.pre(Animate(Padding(Text(device)), "flipInX"), justify="center", text_align="center")
  
  console.append("<div class='p-1 bg-red-500/60 text-center'>SELECT ATTACK</div>")

  div = Div(*[f"""<div class='p-2 border-b text-center' onclick='sendInput("{script}")'>{get_script_name(scripts_meta, script)}</div>""" for script in os.listdir(scripts_path) if script.endswith(".cdb")])
  div.cls.add_class("w-full bg-slate-800/60")

  console.append(Animate(div))

  run_script(device, scripts_path, input())

