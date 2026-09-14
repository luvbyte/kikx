from pathlib import Path


# Get project path
def get_root_path() -> Path:
  return Path(__file__).resolve().parent