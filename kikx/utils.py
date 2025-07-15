from pathlib import Path

def get_root_path():
  return Path(__file__).resolve().parent
