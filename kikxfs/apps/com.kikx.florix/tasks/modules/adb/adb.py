from .device import run, Device

def list_active_devices():
  devices = run("devices")
  
  active = []
  for index, line in enumerate(devices.split("\n")):
    if index == 0:
      continue
    addr, status = line.split()
    if status == "device":
      active.append(Device(addr))
  return active

