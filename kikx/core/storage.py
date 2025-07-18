import logging
from pathlib import Path
import shlex

from lib.utils import ensure_dir

logger = logging.getLogger(__name__)


class Storage:
  """Handles structured directory storage layout for the app."""

  def __init__(self, storage_path: str):
    self.storage_path: Path = ensure_dir(Path(storage_path).resolve())

    if not self.storage_path.is_dir():
      raise Exception("Storage path must be a directory")
    
    # Pre-create important subdirectories
    precreate = ["home", "apps", "share", "data", "data/app", "data/data", "bin", "root"]
    for name in precreate:
      dir_path = self.storage_path / name
      ensure_dir(dir_path)
      logger.debug(f"Ensured directory exists: {dir_path}")

  @property
  def path(self) -> Path:
    """Return the base storage path."""
    return self.storage_path

  def join(self, *path: str) -> Path:
    """Join paths safely under storage root."""
    return self.storage_path.joinpath(*path)
