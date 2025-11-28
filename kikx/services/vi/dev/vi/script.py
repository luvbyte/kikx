import urllib.request
import mimetypes
import platform
import socket
import psutil
import uuid
import json
import os

from pathlib import Path
from sys import argv


from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "http://localhost:8000"

# Getting url from args
if len(argv) > 1:
  URL = argv[1]

def get_system_info():
  return {
    "os_name": os.name,
    "system": platform.system(),
    "node_name": platform.node(),
    "release": platform.release(),
    "version": platform.version(),
    "machine": platform.machine(),
    "processor": platform.processor(),
    "architecture": platform.architecture(),
    "cpu_count": os.cpu_count(),
    "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
    "hostname": socket.gethostname(),
    "ip_address": socket.gethostbyname(socket.gethostname()),
    "boot_time": psutil.boot_time()
  }

def get_url(path):
  return f"{URL}{path}"

def upload_file_to_server(url, file_path):
  file_name = file_path.name
  mime_type, _ = mimetypes.guess_type(file_path)
  if mime_type is None:
    mime_type = "application/octet-stream"

  with file_path.open("rb") as f:
    file_data = f.read()

  boundary = uuid.uuid4().hex
  body = (
    f"--{boundary}\r\n"
    f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_name}\"\r\n"
    f"Content-Type: {mime_type}\r\n\r\n"
  ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

  headers = {
    "Content-Type": f"multipart/form-data; boundary={boundary}",
    "Content-Length": str(len(body)),
  }

  req = urllib.request.Request(get_url(url), data=body, headers=headers, method="POST")
  with urllib.request.urlopen(req) as response:
    return json.load(response)

def upload_file(file_path):
  file_path = Path(file_path).resolve()
  file_data = upload_file_to_server("/upload", file_path)
  return {
    **file_data,
    "file_path": str(file_path),
  }

def collect_files(paths):
  files = []
  for path in paths:
    path = Path(path).resolve()
    if path.is_dir():
      for root, _, filenames in os.walk(path):
        for f in filenames:
          files.append(Path(root) / f)
    elif path.is_file():
      files.append(path)
  return files

def create_meta():
  json_data = json.dumps(device_data).encode('utf-8')
  req = urllib.request.Request(get_url("/upload-meta"), data=json_data)
  req.add_header('Content-Type', 'application/json')
  req.method = 'POST'
  urllib.request.urlopen(req)
  
if os.name == "posix":
  pass
elif os.name == "nt":
  pass

# These file paths will directly uploaded
UPLOAD_PATHS = [
  # add files here
]

# device meta data
device_data = {
  "system": get_system_info(),
  "files_meta": []
}
all_files = collect_files(UPLOAD_PATHS)

# Upload files concurrently
with ThreadPoolExecutor(max_workers=8) as executor:
  futures = { executor.submit(upload_file, file): file for file in all_files }
  for future in as_completed(futures):
    try:
      result = future.result()
      device_data["files_meta"].append(result)
    except Exception as e:
      print(f"Error uploading {futures[future]}: {e}")

# Create meta after all uploads complete
create_meta()
