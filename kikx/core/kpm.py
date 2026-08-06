import json
import shutil

from pathlib import Path
from pydantic import Field

from core.utils import load_app_manifest
from core.models.app_models import AppManifestModel, AppModel, GithubSourceModel

from lib.parser import parse_config
from lib.utils import is_version_match, is_update_available, joinpath



# App install manifest app.json file
class AppInstallManifest(AppManifestModel):
  include: list[str] = Field(default_factory=list)

# ------------- Installers
class AppInstaller:
  def __init__(self, core, src_path: str | Path) -> None:
    self.core = core # Kikx core

    self.status_history: list[str] = ["Installer initializing"]
    self.src_path: Path = Path(src_path).resolve()
    
    app_manifest_path: Path = (self.src_path / "app.json").resolve()
    if not app_manifest_path.is_file():
      raise Exception("app.json not found")

    try:
      self.manifest: AppInstallManifest = parse_config(app_manifest_path, AppInstallManifest)
    except Exception:
      raise Exception("Error parsing app.json")

    # apps/<name>
    # Target app path
    self.target_path: Path = (self.core.config.apps_path / self.manifest.name).resolve()
    self.apps_base_path: Path = self.core.config.apps_path.resolve()
    # data/app
    self.apps_data_base_path: Path = self.core.config.apps_data_path.resolve()
    
    # Status
    self.set_status("Manifest loaded")

  @property # Return new app name
  def app_name(self) -> str:
    return self.manifest.name.strip()

  @property # If app path exists
  def is_app_installed(self) -> bool:
    return self.target_path.exists()

  @property # Check kikx version match
  def is_compatible(self) -> bool:
    return is_version_match(self.core.version, self.manifest.kikx_version)

  @property # If app has update
  def is_update(self) -> bool | dict:
    if not self.is_app_installed:
      return False

    # ------------- Get old manifest
    manifest = load_app_manifest(self.core, self.app_name, raw=True)
    
    # Old app version
    current_version = manifest.version
    # Latest app version
    latest_version = self.manifest.version
    
    # Compare and return if True
    if is_update_available(current_version, latest_version):
      return {
        "current_version": current_version,
        "latest_version": latest_version,
        "current_source": manifest.source,
        "latest_source": self.manifest.source,

        "previous_manifest": manifest
      }

    return False

  # Get source 
  def get_source(self):
    return self.manifest.source

  # State tracking
  def set_status(self, text: str) -> None:
    self.status_history.append(text)

  # Get src app manifest based on keys to include
  def get_manifest(self, keys_to_include=None) -> dict:
    manifest = self.manifest.model_dump()

    if keys_to_include is not None:
      manifest = {
        k: v for k, v in manifest.items()
        if k in keys_to_include
      }

    return manifest

  # Extract App config from manifest
  def get_app_config(self) -> dict:
    return self.get_manifest(list(AppModel.model_fields.keys()))

  # Extract App manifest based on model
  def get_app_manifest(self) -> dict:
    return self.get_manifest(list(AppManifestModel.model_fields.keys()))

  # Install from local or github
  def install(self, source):
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

  # Check source if missmatch raise
  def _source_check(self, current, latest) -> bool:
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
  
  # update app
  def update(self, source) -> bool:
    if not self.is_app_installed:
      raise Exception("App is not installed")

    if not self.is_compatible:
      raise Exception("App is not compatible")

    previous_manifest = load_app_manifest(self.core, self.app_name, raw=True)

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
  def _create_app_directory(self) -> None:
    self.set_status("Creating app folder")

    self.target_path.mkdir(parents=True, exist_ok=False)

    # Safety check
    resolved_target = self.target_path.resolve()
    if not resolved_target.is_relative_to(self.apps_base_path):
      raise ValueError("Unsafe target path detected")

  def _copy_include_files(self) -> None:
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

  def _create_manifest_file(self, source) -> None:
    self.set_status("Creating app manifest file")

    manifest_path = self.target_path / "app.json"
    
    manifest = self.get_app_manifest()
    manifest["source"] = source

    with manifest_path.open("w", encoding="utf-8") as file:
      json.dump(manifest, file, indent=2)

  def _create_config_file(self) -> None:
    self.set_status("Creating app config file")

    self.apps_data_base_path.mkdir(parents=True, exist_ok=True)

    config_path = self.apps_data_base_path / f"{self.app_name}.json"

    with config_path.open("w", encoding="utf-8") as file:
      json.dump(self.get_app_config(), file, indent=2)

  # Rollback (if install fails)
  def _rollback(self) -> None:
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

  def get_status(self) -> list[str]:
    return self.status_history

class UIInstaller:
  def __init__(self, core, name: str, src_path: Path) -> None:
    self.core = core
    self.name: str = name
    self.src_path: Path = src_path

    self.target_path: Path = joinpath(self.core.config.uis_path, name)

  # If already
  def install(self, force: bool = False) -> None:
    if self.target_path.exists() and not force:
      raise Exception("UI already exists.")

    # Remove existing installation if present
    if self.target_path.exists():
      if self.target_path.is_dir():
        shutil.rmtree(self.target_path)
      else:
        self.target_path.unlink()

    # Ensure parent directory exists
    self.target_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy extracted UI into place
    if self.src_path.is_dir():
      shutil.copytree(self.src_path, self.target_path)
    else:
      shutil.copy2(self.src_path, self.target_path)

    user_config = self.core.auth.user_config

    # Register UI
    if self.target_path.name not in user_config.ui:
      user_config.ui.append(self.target_path.name)

    if len(user_config.ui) == 1:
      user_config.default_ui = self.target_path.name
  
    # Save user config
    self.core.auth.save()

# ------------- Uninstallers
class AppUninstaller:
  def __init__(self, core, app_name: str) -> None:
    self.core = core
    self.app_name: str = app_name
    self.status_history: list[str] = ["Uninstaller initialized"]

    # Paths
    self.app_path: Path = self.core.config.apps_path / app_name
    self.config_path: Path = self.core.config.apps_data_path / f"{app_name}.json"
    self.data_path: Path = self.core.config.data_path / "data" / app_name

    self.set_status("Uninstaller initialized")

  def set_status(self, text: str) -> None:
    self.status_history.append(text)
  
  @property
  def admin_apps(self) -> list[str]:
    return self.core.config.admin_apps

  @property
  def is_app_installed(self) -> bool:
    return self.app_path.exists()

  def _ensure_safe_path(self, path: Path, base_path: Path, error_message: str) -> Path:
    resolved_path = path.resolve()
    resolved_base = base_path.resolve()

    if not resolved_path.is_relative_to(resolved_base):
      raise ValueError(error_message)

    return resolved_path

  def uninstall(self, keep_data: bool = False) -> None:
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
    if not keep_data and self.data_path.exists():
      self.set_status("Removing app data directory")

      safe_data_path = self._ensure_safe_path(
        self.data_path,
        base_app_data_root,
        "Unsafe data path detected"
      )

      shutil.rmtree(safe_data_path)

    self.set_status("Uninstall completed")
    return True

  def get_status(self) -> list[str]:
    return self.status_history

class UIUninstaller:
  def __init__(self, core, ui_name: str):
    self.core = core
    self.ui_name: str = ui_name
    
    self.ui_path: Path = joinpath(core.user.uis_path / ui_name)
  
  def uninstall(self):
    if not self.ui_path.exists():
      raise FileNotFoundError("UI not found")

    # Remove installed UI
    if self.ui_path.is_dir():
      shutil.rmtree(self.ui_path)
    else:
      self.ui_path.unlink()

    user_config = self.core.auth.user_config
    ui_name = self.ui_path.name

    # Remove from registered UIs
    if ui_name in user_config.ui:
      user_config.ui.remove(ui_name)

    # Update default UI if necessary
    if user_config.default_ui == ui_name:
      user_config.default_ui = user_config.ui[-1] if user_config.ui else ""

    # Save configuration
    self.core.auth.save()
    return True

