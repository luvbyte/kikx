from typing import Literal

from pydantic import Field

from .base import StrictBaseModel


# ---------------------- Storage
StorageName = Literal["root", "home", "os", "osr"]
StorageType = Literal["none", "read", "write", "read-write"]


class FSConfigModel(StrictBaseModel):
  root: StorageType = Field(
    default="none",
    description="Root storage permission",
  )

  os: StorageType = Field(
    default="none",
    description="OS home storage permission",
  )

  osr: StorageType = Field(
    default="none",
    description="OS root storage permission",
  )

  home: StorageType = Field(
    default="none",
    description="Home storage permission",
  )


# ---------------------- Tasker
class TaskerConfigModel(StrictBaseModel):
  shell: bool = False

  # KIKX_ environment variables
  kikx_env: bool = True

  # If False, use the program environment
  sandbox: bool = False

  # Custom environment variables
  env: dict[str, str] = Field(default_factory=dict)

  # Main program used to run tasks
  main: str = Field(
    "{python} -u {app}/tasks/{name}.py {args}",
    description="Prefix for all tasks",
  )


# ---------------------- Micro
class MicroConfigModel(StrictBaseModel):
  main: str = "main.py"

  # Capture stdout and save
  stdout: bool = False

  # Make persistent
  persistent: bool = False

# ---------------------- Service Config
class ServiceConfigModel(StrictBaseModel):
  tasker: TaskerConfigModel | None = None
  fs: FSConfigModel | None = None
  micro: dict[str, MicroConfigModel] | None = None