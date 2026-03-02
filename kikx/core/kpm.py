# Kikx Package Manager
from pathlib import Path

from lib.parser import parse_config
from core.models.app_models import AppManifestModel, AppModel, GithubSourceModel

from typing import List
import shutil
import json
import time

import tempfile
import zipfile
import subprocess
from urllib.parse import urlparse
import urllib.request

from lib.hash import hash_file
from lib.utils import is_version_ok, is_update_available, generate_uuid


from fastapi import HTTPException



GITHUB_API = "https://api.github.com/repos"

class AppInstallManifest(AppManifestModel):
  include: List[str] = []


# ------------- Installer
class AppInstaller:
  def __init__(self, core, src_path: str | Path):
    self.status_history = ["Installer initializing"]
    self.core = core
    self.src_path = Path(src_path).resolve()

    # Load manifest
    self.manifest = parse_config(
      self.src_path / "app.manifest.json",
      AppInstallManifest
    )

    # Target paths
    # apps/<name>
    self.target_path = (self.core.config.apps_path / self.manifest.name).resolve()
    self.apps_base_path = self.core.config.apps_path.resolve()
    # data/app
    self.apps_data_base_path = self.core.config.apps_data_path.resolve()

    self.set_status("Manifest loaded")

  @property
  def app_name(self) -> str:
    return self.manifest.name.strip()
  
  @property
  def is_app_installed(self) -> bool:
    return self.target_path.exists()

  @property
  def is_compatible(self):
    return is_version_ok(self.core.version, self.manifest.kikx_version)

  # If its an update / obj / None
  @property
  def is_update(self):
    if not self.is_app_installed:
      return False
    
    # ------------- Get old manifest
    manifest = self.core.user.load_app_manifest(self.app_name)
    
    current_version = manifest.version
    latest_version = self.manifest.version

    if is_update_available(current_version, latest_version):
      return {
        "current_version": current_version,
        "latest_version": latest_version,
        "current_source": manifest.source,
        "latest_source": self.manifest.source,

        "previous_manifest": manifest
      }

    return False

  def get_source(self):
    return self.manifest.source

  def set_status(self, text: str) -> None:
    self.status_history.append(text)

  def get_manifest(self, keys_to_include=None) -> dict:
    manifest = self.manifest.model_dump()

    if keys_to_include is not None:
      manifest = {
        k: v for k, v in manifest.items()
        if k in keys_to_include
      }

    return manifest

  def get_app_config(self) -> dict:
    return self.get_manifest(list(AppModel.model_fields.keys()))

  def get_app_manifest(self) -> dict:
    return self.get_manifest(list(AppManifestModel.model_fields.keys()))

  # local / github {}
  def install(self, source) -> bool:
    if not self.is_compatible:
      raise Exception("App is not compatible")

    # If app already installed
    if self.is_app_installed:
      return self.update(source)

    try:
      self._create_app_directory()
      self._copy_include_files()
      self._create_manifest_file(source)
      self._create_config_file()

      self.set_status("Install completed")

      return True
    except Exception as e:
      self.set_status(f"Install failed: {e}")
      self._rollback()
      raise
  
  # Check source it missmatch raise
  def _source_check(self, current, latest):
    # If both local matched
    if current == "local" and latest == "local":
      return True

    # If one local, one github -> mismatch
    if current == "local" or latest == "local":
      raise Exception("Source mismatch: one is local and the other is GitHub")
    
    latest = GithubSourceModel(**latest)

    # Both GitHub match
    if isinstance(current, GithubSourceModel) and isinstance(latest, GithubSourceModel):
      if current.owner != latest.owner:
        raise Exception("GitHub owner mismatch")

      if current.repo != latest.repo:
        raise Exception("GitHub repo mismatch")

      return True

    raise Exception("Invalid source configuration")

  def update(self, source) -> bool:
    if not self.is_app_installed:
      raise Exception("App is not installed")
    
    if not self.is_compatible:
      raise Exception("App is not compatible")
    
    previous_manifest = self.core.user.load_app_manifest(self.app_name)

    # check source matched
    self._source_check(previous_manifest.source, source)
    
    # only install latest version cant install lesser
    if not self.is_update:
      raise Exception("App already installed")

    try:
      self.set_status("Starting update")

      # Backup existing app
      backup_path = self.target_path.with_suffix(".backup")
      if backup_path.exists():
        shutil.rmtree(backup_path)

      self.set_status("Creating backup")
      shutil.move(self.target_path, backup_path)

      try:
        # Recreate fresh directory
        self._create_app_directory()
        self._copy_include_files()
        self._create_manifest_file(source)
        # update app config here
        self._create_config_file()

        self.set_status("Update completed")

        # Remove backup after success
        shutil.rmtree(backup_path)

        return True
      except Exception:
        # Restore backup on failure
        self.set_status("Update failed — restoring backup")

        if self.target_path.exists():
          shutil.rmtree(self.target_path)

        shutil.move(backup_path, self.target_path)

        raise

    except Exception as e:
      self.set_status(f"Update failed: {e}")
      raise

  # ------------- Install steps
  def _create_app_directory(self):
    self.set_status("Creating app folder")

    self.target_path.mkdir(parents=True, exist_ok=False)

    # Safety check
    resolved_target = self.target_path.resolve()
    if not resolved_target.is_relative_to(self.apps_base_path):
      raise ValueError("Unsafe target path detected")

  def _copy_include_files(self):
    self.set_status("Copying include files")

    base_path = self.src_path.resolve()

    for name in self.manifest.include:
      candidate = base_path / name
      resolved_src = candidate.resolve()

      # Security check (prevent ../../ traversal)
      if not resolved_src.is_relative_to(base_path):
        raise ValueError(f"Unsafe path detected: {name}")

      if not resolved_src.exists():
        raise FileNotFoundError(f"Include file not found: {name}")

      dst = self.target_path / resolved_src.name

      if resolved_src.is_dir():
        shutil.copytree(resolved_src, dst, dirs_exist_ok=False)
      else:
        shutil.copy2(resolved_src, dst)

  def _create_manifest_file(self, source):
    self.set_status("Creating app manifest file")

    manifest_path = self.target_path / "app.json"
    
    manifest = self.get_app_manifest()
    manifest["source"] = source

    with manifest_path.open("w", encoding="utf-8") as file:
      json.dump(manifest, file, indent=2)

  def _create_config_file(self):
    self.set_status("Creating app config file")

    self.apps_data_base_path.mkdir(parents=True, exist_ok=True)

    config_path = self.apps_data_base_path / f"{self.app_name}.json"

    with config_path.open("w", encoding="utf-8") as file:
      json.dump(self.get_app_config(), file, indent=2)

  # Rollback (if install fails)
  def _rollback(self):
    self.set_status("Rolling back installation")

    if self.target_path.exists():
      resolved_target = self.target_path.resolve()

      if resolved_target.is_relative_to(self.apps_base_path):
        shutil.rmtree(resolved_target)

    config_path = self.apps_data_base_path / f"{self.app_name}.json"
    if config_path.exists():
      resolved_config = config_path.resolve()

      if resolved_config.is_relative_to(self.apps_data_base_path):
        config_path.unlink()

    self.set_status("Rollback completed")

  def get_status(self):
    return self.status_history


# ------------- Uninstaller

class AppUninstaller:
  def __init__(self, core, app_name: str):
    self.core = core
    self.app_name = app_name
    self.status_history = ["Uninstaller initialized"]

    # Paths
    self.app_path = self.core.config.apps_path / app_name
    self.config_path = self.core.config.apps_data_path / f"{app_name}.json"
    self.data_path = self.core.config.data_path / "data" / app_name

    self.set_status("Uninstaller initialized")

  def set_status(self, text: str):
    self.status_history.append(text)
  
  @property
  def admin_apps(self):
    return self.core.config.admin_apps

  @property
  def is_app_installed(self) -> bool:
    return self.app_path.exists()

  def _ensure_safe_path(self, path, base_path, error_message):
    resolved_path = path.resolve()
    resolved_base = base_path.resolve()

    if not resolved_path.is_relative_to(resolved_base):
      raise ValueError(error_message)

    return resolved_path

  def uninstall(self, no_data: bool = False):
    if not self.is_app_installed:
      raise Exception("App is not installed")

    if self.app_name in self.admin_apps:
      raise Exception("Cant remove admin app")

    base_apps_path = self.core.config.apps_path
    base_config_path = self.core.config.apps_data_path
    base_app_data_root = self.core.config.data_path / "data"

    # Remove app directory
    self.set_status("Removing app directory")

    safe_app_path = self._ensure_safe_path(
      self.app_path,
      base_apps_path,
      "Unsafe app path detected"
    )

    shutil.rmtree(safe_app_path)

    # Remove config file
    self.set_status("Removing app config file")

    if self.config_path.exists():
      safe_config_path = self._ensure_safe_path(
        self.config_path,
        base_config_path,
        "Unsafe config path detected"
      )

      safe_config_path.unlink()

    # Remove app data directory (optional)
    if not no_data and self.data_path.exists():
      self.set_status("Removing app data directory")

      safe_data_path = self._ensure_safe_path(
        self.data_path,
        base_app_data_root,
        "Unsafe data path detected"
      )

      shutil.rmtree(safe_data_path)

    self.set_status("Uninstall completed")
    return True
  
  def get_status(self):
    return self.status_history


# ------------- Utils
def resolve_app_package(uri: str | Path, temp_dir: Path | None = None) -> Path:
  path = Path(uri).resolve()

  if not path.exists():
    raise FileNotFoundError("App package not found")

  if path.suffix != ".kikx":
    raise ValueError("Only .kikx packages are supported")

  # Create temp_dir if not provided
  if temp_dir is None:
    temp_dir = Path(tempfile.mkdtemp())
  else:
    temp_dir = Path(temp_dir).resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)

  # Security: ensure temp_dir exists
  if not temp_dir.exists():
    raise RuntimeError("Failed to create temp directory")

  with zipfile.ZipFile(path, "r") as zip_ref:
    for member in zip_ref.namelist():
      member_path = temp_dir / member

      # Prevent zip-slip
      if not member_path.resolve().is_relative_to(temp_dir.resolve()):
        raise ValueError("Unsafe file detected inside package")

    zip_ref.extractall(temp_dir)

  extracted_dirs = [p for p in temp_dir.iterdir() if p.is_dir()]

  if len(extracted_dirs) != 1:
    raise ValueError("Invalid app structure")

  return extracted_dirs[0]


def parse_github_repo(repo_url: str) -> tuple[str, str]:
  parsed = urlparse(repo_url)

  if parsed.netloc not in ("github.com", "www.github.com"):
    raise HTTPException(400, "Invalid GitHub URL")

  parts = parsed.path.strip("/").split("/")
  if len(parts) < 2:
    raise HTTPException(400, "Invalid GitHub repository URL")

  return parts[0], parts[1]


