from pathlib import Path

class ShortLink:
  def __init__(self, links_path: Path):
    self.links_path = links_path

  def resolve(self, path):
    file_path = self.links_path / path
    if not file_path.exists() or file_path.is_dir():
      raise Exception("Not found")
    
    with open(file_path, "r") as file:
      return file.read().strip()

