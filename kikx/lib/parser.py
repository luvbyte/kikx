import json
import tomli
import yaml
import logging

from pathlib import Path
from typing import IO, Any, Optional, Type, Union
from pydantic import BaseModel, ValidationError

from core.errors import raise_error

logger = logging.getLogger(__name__)


def parse_file(
  file: IO,
  model: Optional[Type[BaseModel]] = None,
  parse_type: str = "json"
) -> Any:
  """
  Parse a config file (JSON, YAML, TOML) into a dict or a Pydantic model.

  Args:
    file: Opened file object.
    model: Optional Pydantic model class.
    parse_type: Format type: 'json', 'yaml', or 'toml'.

  Returns:
    Parsed dict or model instance.
  """
  try:
    if parse_type == "json":
      data = json.load(file)
    elif parse_type == "yaml":
      data = yaml.safe_load(file)
    elif parse_type == "toml":
      data = tomli.load(file)
    else:
      raise_error(f"Unsupported parse type: {parse_type}")
  except Exception as e:
    raise_error(f"Failed to parse file as {parse_type}: {e}")

  if model is None:
    return data

  try:
    return model.model_validate(data)
  except ValidationError as e:
    logger.error(f"Validation failed for model {model.__name__}: {e}")
    raise_error(f"Invalid structure for model {model.__name__}")


def parse_config(
  file_path: Union[str, Path],
  model: Optional[Type[BaseModel]] = None,
  parse_type: str = "json"
) -> Any:
  """
  Parse a config file from disk using the specified model and format.

  Args:
    file_path: Path to config file.
    model: Optional Pydantic model class.
    parse_type: Format: 'json', 'yaml', or 'toml'.

  Returns:
    Parsed object or validated model instance.
  """
  try:
    mode = "rb" if parse_type == "toml" else "r"
    with open(file_path, mode) as file:
      return parse_file(file, model, parse_type)
  except FileNotFoundError:
    raise_error(f"Config file not found: {file_path}")
  except json.JSONDecodeError:
    raise_error(f"Invalid JSON format: {file_path}")
  except yaml.YAMLError:
    raise_error(f"Invalid YAML format: {file_path}")
  except tomli.TOMLDecodeError:
    raise_error(f"Invalid TOML format: {file_path}")
  except Exception as e:
    raise_error(f"Unexpected error parsing {file_path}: {e}")
