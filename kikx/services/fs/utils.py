import os
import stat
import mimetypes

from PIL import Image
from pathlib import Path
from datetime import datetime

from lib.utils import joinpath
from .config import IMAGE_EXTENSIONS, FORMAT_MAP




def to_list(value):
  return value if isinstance(value, list) else [value]

# ---------------------- Path Info

def get_path_info(path: Path, kikxpath: str) -> dict:
  try:
    stat_result = path.stat()
  except OSError:
    return {
      "name": path.name,
      "stem": path.stem,
      "suffix": path.suffix,
      "directory": None,
      "items_count": None,
      "absolute_path": str(path.absolute()),
      "kikxpath": kikxpath,
      "size_bytes": None,
      "created": None,
      "modified": None,
      "accessed": None,
      "owner": None,
      "group": None,
      "permissions": None,
      "exists": None,
      "is_file": None,
      "is_symlink": None,
      "image_type": path.suffix.lower() in IMAGE_EXTENSIONS,
      "mime_type": None,
      "encoding": None,
    }

  mode = stat_result.st_mode
  is_dir = stat.S_ISDIR(mode)
  is_file = stat.S_ISREG(mode)
  is_symlink = stat.S_ISLNK(mode)

  try:
    owner = path.owner()
  except (KeyError, OSError):
    owner = str(stat_result.st_uid)

  try:
    group = path.group()
  except (KeyError, OSError):
    group = str(stat_result.st_gid)

  items_count = None

  if is_dir:
    try:
      with os.scandir(path) as entries:
        items_count = sum(1 for _ in entries)
    except OSError:
      items_count = 0

  suffix = path.suffix
  mime_type, encoding = mimetypes.guess_type(path.name)

  return {
    "name": path.name,
    "stem": path.stem,
    "suffix": suffix,
    "directory": is_dir,
    "items_count": items_count,
    "absolute_path": str(path.absolute()),
    "kikxpath": kikxpath,
    "size_bytes": stat_result.st_size,
    "created": datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
    "modified": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
    "accessed": datetime.fromtimestamp(stat_result.st_atime).isoformat(),
    "owner": owner,
    "group": group,
    "permissions": oct(stat.S_IMODE(mode)),
    "exists": True,
    "is_file": is_file,
    "is_symlink": is_symlink,
    "image_type": suffix.lower() in IMAGE_EXTENSIONS,
    "mime_type": mime_type,
    "encoding": encoding,
  }


# ---------------------- Unique Path

def get_unique_path(path: str | Path) -> Path:
  path = Path(path)

  if not path.exists():
    return path

  counter = 1

  while True:
    if path.is_file():
      candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
    else:
      candidate = path.with_name(f"{path.name} ({counter})")

    if not candidate.exists():
      return candidate

    counter += 1


# ---------------------- Thumbnail
def generate_thumbnail(
  path: Path,
  size: tuple[int, int] = (200, 200),
) -> Path | None:
  if not path.exists() or not path.is_file():
    return None

  ext = path.suffix.lower()

  if ext not in IMAGE_EXTENSIONS:
    return None

  # Keep GIFs animated.
  if ext == ".gif":
    return path

  # Already a thumbnail.
  if path.parent.name == ".thumbnails":
    return path

  thumbnail_dir = path.parent / ".thumbnails"
  thumbnail_dir.mkdir(parents=True, exist_ok=True)

  thumbnail_path = thumbnail_dir / path.name

  if thumbnail_path.exists():
    return thumbnail_path

  try:
    with Image.open(path) as img:
      img.thumbnail(size)

      if FORMAT_MAP[ext] == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

      img.save(thumbnail_path, FORMAT_MAP[ext])

    return thumbnail_path

  except Exception:
    return None


# ---------------------- Delete Thumbnail

def delete_thumbnail(path: Path) -> bool:
  if not path.exists() or not path.is_file():
    return False

  ext = path.suffix.lower()

  # GIFs don't have generated thumbnails.
  if ext == ".gif":
    return False

  if ext not in IMAGE_EXTENSIONS:
    return False

  # Don't delete if this is already a thumbnail.
  if path.parent.name == ".thumbnails":
    return False

  thumbnail_path = joinpath(
    path.parent / ".thumbnails",
    path.name,
  )

  if not thumbnail_path.exists():
    return False

  try:
    thumbnail_path.unlink()

    # Remove the thumbnail directory if it's empty.
    try:
      thumbnail_path.parent.rmdir()
    except OSError:
      pass

    return True

  except Exception:
    return False