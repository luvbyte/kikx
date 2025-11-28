from .process import sh
from uuid import uuid4
import re

# List of devices attached
# localhost:35869 device

def cmd(text):
  return sh(f"adb {text}")

def run(text, output=True):
  proc = cmd(text).run()
  if output:
    return proc.output()
  else:
    return proc

class Device:
  def __init__(self, addr):
    self.addr = addr
  
    self.model = self.shell("getprop ro.product.model").strip()
    self.manufacturer = self.shell("getprop ro.product.manufacturer").strip()
    self.android_version = self.shell("getprop ro.build.version.release").strip()
    self.sdk_version = self.shell("getprop ro.build.version.sdk").strip()
  
    self.state = self.run("get-state").strip()
    self.serial = self.run("get-serialno").strip()
  
  def save_screen_shot(self, storage):
    image_path = f"/sdcard/{uuid4().hex}.png"
    self.shell(f"screencap {image_path}")
    self.pull(image_path, storage, remove=True)
  
  def pull(self, remote, local, remove=False):
    output = self.run(f"pull {remote} {local}", output=False)
    if remove:
      self.shell(f"rm {remote}")
    return output

  def push(self, local, remote):
    return self.run(f"push {local} {remote}", output=False)

  def run(self, cmd, output=True):
    return run(f"-s {self.addr} {cmd}", output=output)

  def shell(self, cmd, output=True):
    return self.run(f"shell {cmd}", output=output)

  def __str__(self):
    return (f"Device: {self.addr}\n"
            f"Manufacturer: {self.manufacturer}\n"
            f"Model: {self.model}\n"
            f"Android Version: {self.android_version}\n"
            f"SDK Version: {self.sdk_version}\n"
            f"State: {self.state}\n"
            f"Serial: {self.serial}"
          )


