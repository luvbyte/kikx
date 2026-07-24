from pathlib import Path

from lib.utils import ensure_dir, joinpath


class Storage:
  def __init__(self, storage_path: str) -> None:
    self.storage_path: Path = Path(storage_path)
    
    if not self.storage_path.exists():
      raise Exception("Storage path not found")

    if not self.storage_path.is_dir():
      raise Exception("Storage path must be a directory")
    
    # Pre-create important subdirectories if not exists
    precreate = [
      "home", "apps", "share",
      "data", "data/app","data/data",
      "bin", "root", "etc", "logs"
    ]
    for name in precreate:
      ensure_dir(self.storage_path / name)

  @property
  def path(self) -> Path:
    return self.storage_path
  
  def info(self) -> dict:
    return {
      "path": str(self.path),
    }

  def join(self, *parts: str | Path) -> Path:
    return joinpath(self.storage_path, *parts)
