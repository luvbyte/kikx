import json
# import tomli
# import yaml
import logging

from pathlib import Path
from typing import IO, Any, Optional, Type, Union
from pydantic import BaseModel, ValidationError


def parse_file(
  file: IO,
  model: Optional[Type[BaseModel]] = None,
  parse_type: str = "json"
) -> Any:
  try:
    if parse_type == "json":
      data = json.load(file)
    else:
      raise ValueError(f"Unsupported parse type: {parse_type}")
  except Exception as e:
    raise ValueError(f"Failed to parse file as {parse_type}") from e

  if model is None:
    return data

  try:
    return model.model_validate(data)
  except ValidationError as e:
    raise ValueError(f"Invalid structure for model {model.__name__}") from e


def parse_config(
  file_path: Union[str, Path],
  model: Optional[Type[BaseModel]] = None,
  parse_type: str = "json"
) -> Any:
  file_path = Path(file_path)

  try:
    mode = "rb" if parse_type == "toml" else "r"
    with open(file_path, mode) as file:
      return parse_file(file, model, parse_type)

  except FileNotFoundError as e:
    raise FileNotFoundError(f"Config file not found: {file_path}") from e

  except json.JSONDecodeError as e:
    raise ValueError(f"Invalid {parse_type.upper()} format in {file_path}") from e

  except Exception as e:
    raise RuntimeError(f"Unexpected error parsing {file_path}") from e
