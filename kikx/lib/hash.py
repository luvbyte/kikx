import hashlib
from pathlib import Path

def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
  hasher = hashlib.sha256()

  with path.open("rb") as f:
    while chunk := f.read(chunk_size):
      hasher.update(chunk)

  return hasher.hexdigest()
