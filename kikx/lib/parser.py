import json

from pathlib import Path
from typing import IO, Any, Optional, Type, Union, Generic, TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


def load_or_create_config(path: Path, model: Type[T]) -> T:
  try:
    data = path.read_json()
    return model.model_validate(data)

  except Exception:
    config = model()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    return config


def parse_file(file: IO, model: Optional[Type[BaseModel]] = None) -> Any:
  try:
    data = json.load(file)
  except Exception as e:
    raise ValueError("Failed to parse file") from e

  if model is None:
    return data

  try:
    return model.model_validate(data)
  except ValidationError as e:
    raise ValueError(f"Invalid structure for model {model.__name__}") from e


def parse_config(file_path: Union[str, Path], model: Optional[Type[BaseModel]] = None) -> Any:
  file_path = Path(file_path)

  try:
    with open(file_path, "r") as file:
      return parse_file(file, model)

  except FileNotFoundError as e:
    raise FileNotFoundError(f"Config file not found: {file_path}") from e

  except json.JSONDecodeError as e:
    raise ValueError(f"Invalid Json format in {file_path}") from e

  except Exception as e:
    raise RuntimeError(f"Unexpected error parsing {file_path}") from e


class ParseConfig(Generic[T]):
  def __init__(self, path: Path, model: type[T], lorc=False) -> None:
    self.path = path
    self.model = model

    try:
      self.load()
    except Exception:
      if not lorc:
        raise
      self.set_default_config()

  @property
  def data(self) -> T:
    return self._data

  @property
  def data_obj(self) -> dict:
    return self.data.model_dump()

  def set_default_config(self):
    self._data = self.model()
    self.save()

  def load(self) -> T:
    self._data = parse_config(self.path, self.model)
    return self._data

  def save(self) -> None:
    self.path.write_text(self.data.model_dump_json(indent=2), encoding="utf-8")