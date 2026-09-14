from pathlib import Path

from core.models.kikx import KikxConfigModel


# ---------------------- Setup FS
class SetupFS:
  def __init__(self, path: str | Path):
    self.fs_path = Path(path)
    self.fs_path.mkdir(parents=True, exist_ok=True)

    self._pre_create_paths = [
      "apps", "bin", "config",
      "data/app", "data/data",
      "etc", "home", "temp", "ui", "logs",
      "share", "home/share/images/bg",
    ]

  def ensure_dir(self, path, parents=True, exist_ok=True) -> Path:
    path = self.fs_path / path
    path.mkdir(parents=parents, exist_ok=exist_ok)
    return path

  def ensure_dirs(self, *paths) -> None:
    for path in paths:
      self.ensure_dir(path)

  def pre_create(self):
    self.ensure_dirs(*self._pre_create_paths)

  def create_config(self, path: Path, data) -> None:
    path.write_text(data.model_dump_json(indent=2), encoding="utf-8")

  def setup_config(self, config):
    config = KikxConfigModel(**config)
    self.create_config(self.fs_path / "config/kikx.json", config)