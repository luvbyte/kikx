import json
from core.errors import raise_error


def parse_file(file, model, parse_type = "json"):
  if model is None and parse_type == "json":
    return json.load(file)
  elif parse_type == "json":
    return model(**json.load(file))
  else:
    raise_error(f"Parse type not found : {parse_type}")

def parse_config(file_path, model = None, parse_type = "json"):
  try:
    with open(file_path, "r") as file:
      return parse_file(file, model, parse_type)
  except FileNotFoundError:
    raise_error(f"Error: The file '{file_path}' was not found.")
  except json.JSONDecodeError:
    raise_error(f"Error: The file '{file_path}' contains invalid JSON.")
  except TypeError as e:
    raise_error(f"Error: Incorrect data format for model '{model.__name__}': {e}")
  except Exception as e:
    raise_error(f"Error parsing config file[{file_path}]: {e}")
