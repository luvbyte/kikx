import importlib.util
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = PROJECT_ROOT / "kikx"
if str(APP_ROOT) not in sys.path:
  sys.path.insert(0, str(APP_ROOT))


def load_module(name: str, path: Path):
  spec = importlib.util.spec_from_file_location(name, path)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  sys.modules[name] = module
  spec.loader.exec_module(module)
  return module


def test_volumes_environment_value_is_a_path(tmp_path, monkeypatch):
  with monkeypatch.context() as env:
    env.setenv("KIKX_VOLUMES", str(tmp_path / "volumes"))
    config_setup = load_module(
      "config_setup_env_test",
      APP_ROOT / "config" / "setup.py",
    )
    assert config_setup.VOLUMES_PATH == tmp_path / "volumes"


def test_ask_storage_path_stays_inside_volumes(tmp_path, monkeypatch):
  outside = tmp_path.parent / "outside"
  (tmp_path / "escape").symlink_to(tmp_path.parent, target_is_directory=True)

  class Prompt:
    answers = [
      "../outside",
      str(outside),
      ".",
      "escape/child",
      "safe-storage",
    ]
    error_count = 0

    def ask(self, *_args):
      return self.answers.pop(0)

    def error(self, _message):
      self.error_count += 1

  prompt = Prompt()
  setup_module = load_module("kikx_setup_test", APP_ROOT / "setup.py")
  monkeypatch.setattr(setup_module, "VOLUMES_PATH", tmp_path)
  monkeypatch.setattr(setup_module, "scr", prompt)

  assert setup_module.ask_storage_path() == tmp_path / "safe-storage"
  assert prompt.error_count == 4


def test_docker_initialization_preserves_existing_config(tmp_path, monkeypatch):
  entrypoint_path = PROJECT_ROOT / "docker-entrypoint.py"
  entrypoint = load_module("docker_entrypoint_test", entrypoint_path)

  monkeypatch.setattr(entrypoint, "VOLUMES_PATH", tmp_path)
  monkeypatch.setattr(entrypoint, "STORAGE_NAME", "storage")
  monkeypatch.setenv("KIKX_ACCESS_KEY", "first-key")
  monkeypatch.setenv("KIKX_USERNAME", "test-user")

  entrypoint.initialize_storage()
  config_path = tmp_path / "storage" / "config" / "kikx.json"
  initial_config = config_path.read_text(encoding="utf-8")

  monkeypatch.setenv("KIKX_ACCESS_KEY", "replacement-key")
  entrypoint.initialize_storage()

  assert config_path.read_text(encoding="utf-8") == initial_config
  assert '"access": "first-key"' in initial_config
