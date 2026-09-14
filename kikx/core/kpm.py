import json
import shutil

from pathlib import Path

from pydantic import Field

from config.setup import PRE_INSTALL_APPS
from core.models.app import AppManifestModel, AppModel, GithubSourceModel
from core.utils import load_app_manifest
from lib.parser import parse_config
from lib.utils import is_update_available, is_version_match, joinpath


# ---------------------- App Install Manifest
class AppInstallManifest(AppManifestModel):
  include: list[str] = Field(default_factory=list)


# ---------------------- App Installer
class AppInstaller:
  def __init__(self, core, src_path: str | Path) -> None:
    self.core = core
    self.src_path: Path = Path(src_path).resolve()

    app_manifest_path = self.src_path / "app.json"

    if not app_manifest_path.is_file():
      raise Exception("app.json not found")

    try:
      self.manifest: AppInstallManifest = parse_config(
        app_manifest_path,
        AppInstallManifest,
      )
    except Exception:
      raise Exception("Error parsing app.json")

    self.target_path: Path = (
      self.core.config.apps_path / self.manifest.name
    ).resolve()

    self.apps_base_path: Path = self.core.config.apps_path.resolve()
    self.apps_data_base_path: Path = self.core.config.apps_data_path.resolve()

  @property
  def app_name(self) -> str:
    return self.manifest.name.strip()

  @property
  def is_app_installed(self) -> bool:
    return self.target_path.exists()

  @property
  def is_compatible(self) -> bool:
    return is_version_match(
      self.core.version,
      self.manifest.kikx_version,
    )

  @property
  def is_update(self) -> bool | dict:
    if not self.is_app_installed:
      return False

    manifest = load_app_manifest(self.core, self.app_name, raw=True)
    current_version = manifest.version
    latest_version = self.manifest.version

    if is_update_available(current_version, latest_version):
      return {
        "current_version": current_version,
        "latest_version": latest_version,
        "current_source": manifest.source,
        "latest_source": self.manifest.source,
        "previous_manifest": manifest,
      }

    return False

  def get_source(self):
    return self.manifest.source

  def get_manifest(self, keys_to_include=None) -> dict:
    manifest = self.manifest.model_dump()

    if keys_to_include is not None:
      manifest = {
        key: value
        for key, value in manifest.items()
        if key in keys_to_include
      }

    return manifest

  def get_app_config(self) -> dict:
    return self.get_manifest(list(AppModel.model_fields.keys()))

  def get_app_manifest(self) -> dict:
    return self.get_manifest(list(AppManifestModel.model_fields.keys()))

  # ---------------------- Install
  def install(self, source) -> bool:
    if not self.is_compatible:
      raise Exception("App is not compatible")

    if self.is_app_installed:
      return self.update(source)

    try:
      self._create_app_directory()
      self._copy_include_files()
      self._create_manifest_file(source)
      self._create_config_file()
      return True
    except Exception:
      self._rollback()
      raise

  def _source_check(self, current, latest) -> bool:
    if current == "local" and latest == "local":
      return True

    if current == "local" or latest == "local":
      raise Exception(
        "Source mismatch: one is local and the other is GitHub"
      )

    latest = GithubSourceModel(**latest)

    if isinstance(current, GithubSourceModel) and isinstance(
      latest,
      GithubSourceModel,
    ):
      if current.owner != latest.owner:
        raise Exception("GitHub owner mismatch")

      if current.repo != latest.repo:
        raise Exception("GitHub repo mismatch")

      return True

    raise Exception("Invalid source configuration")

  # ---------------------- Update
  def update(self, source) -> bool:
    if not self.is_app_installed:
      raise Exception("App is not installed")

    if not self.is_compatible:
      raise Exception("App is not compatible")

    previous_manifest = load_app_manifest(
      self.core,
      self.app_name,
      raw=True,
    )

    self._source_check(previous_manifest.source, source)

    if not self.is_update:
      raise Exception("App already installed")

    backup_path = self.target_path.with_suffix(".backup")

    if backup_path.exists():
      shutil.rmtree(backup_path)

    shutil.move(self.target_path, backup_path)

    try:
      self._create_app_directory()
      self._copy_include_files()
      self._create_manifest_file(source)
      self._create_config_file()

      shutil.rmtree(backup_path)
      return True

    except Exception:
      if self.target_path.exists():
        shutil.rmtree(self.target_path)

      shutil.move(backup_path, self.target_path)
      raise

  # ---------------------- Install Steps
  def _create_app_directory(self) -> None:
    self.target_path.mkdir(parents=True, exist_ok=False)

    resolved_target = self.target_path.resolve()

    if not resolved_target.is_relative_to(self.apps_base_path):
      raise ValueError("Unsafe target path detected")

  def _copy_include_files(self) -> None:
    base_path = self.src_path.resolve()

    for name in self.manifest.include:
      candidate = base_path / name
      resolved_src = candidate.resolve()

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
    manifest_path = self.target_path / "app.json"

    manifest = self.get_app_manifest()
    manifest["source"] = source

    with manifest_path.open("w", encoding="utf-8") as file:
      json.dump(manifest, file, indent=2)

  def _create_config_file(self) -> None:
    self.apps_data_base_path.mkdir(parents=True, exist_ok=True)

    config_path = self.apps_data_base_path / f"{self.app_name}.json"

    with config_path.open("w", encoding="utf-8") as file:
      json.dump(self.get_app_config(), file, indent=2)

  # ---------------------- Rollback
  def _rollback(self) -> None:
    if self.target_path.exists():
      resolved_target = self.target_path.resolve()

      if resolved_target.is_relative_to(self.apps_base_path):
        shutil.rmtree(resolved_target)

    config_path = self.apps_data_base_path / f"{self.app_name}.json"

    if config_path.exists():
      resolved_config = config_path.resolve()

      if resolved_config.is_relative_to(self.apps_data_base_path):
        resolved_config.unlink()


# ---------------------- UI Installer
class UIInstaller:
  def __init__(self, core, name: str, src_path: Path) -> None:
    self.core = core
    self.name: str = name
    self.src_path: Path = src_path
    self.target_path: Path = joinpath(self.core.config.uis_path, name)

  def install(self, force: bool = False) -> None:
    if self.target_path.exists() and not force:
      raise Exception("UI already exists.")

    if self.target_path.exists():
      if self.target_path.is_dir():
        shutil.rmtree(self.target_path)
      else:
        self.target_path.unlink()

    self.target_path.parent.mkdir(parents=True, exist_ok=True)

    if self.src_path.is_dir():
      shutil.copytree(self.src_path, self.target_path)
    else:
      shutil.copy2(self.src_path, self.target_path)


# ---------------------- App Uninstaller
class AppUninstaller:
  def __init__(self, core, app_name: str) -> None:
    self.core = core
    self.app_name: str = app_name

    self.app_path: Path = self.core.config.apps_path / app_name
    self.config_path: Path = (
      self.core.config.apps_data_path / f"{app_name}.json"
    )
    self.data_path: Path = self.core.config.data_path / "data" / app_name

  @property
  def admin_apps(self) -> list[str]:
    return self.core.config.admin_apps

  @property
  def is_app_installed(self) -> bool:
    return self.app_path.exists()

  def _ensure_safe_path(
    self,
    path: Path,
    base_path: Path,
    error_message: str,
  ) -> Path:
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

    safe_app_path = self._ensure_safe_path(
      self.app_path,
      self.core.config.apps_path,
      "Unsafe app path detected",
    )

    shutil.rmtree(safe_app_path)

    if self.config_path.exists():
      safe_config_path = self._ensure_safe_path(
        self.config_path,
        self.core.config.apps_data_path,
        "Unsafe config path detected",
      )
      safe_config_path.unlink()

    if not keep_data and self.data_path.exists():
      safe_data_path = self._ensure_safe_path(
        self.data_path,
        self.core.config.data_path / "data",
        "Unsafe data path detected",
      )
      shutil.rmtree(safe_data_path)

    return True


# ---------------------- UI Uninstaller
class UIUninstaller:
  def __init__(self, core, ui_name: str):
    self.core = core
    self.ui_name: str = ui_name
    self.ui_path: Path = joinpath(core.user.uis_path / ui_name)

  def uninstall(self):
    if not self.ui_path.exists():
      raise FileNotFoundError("UI not found")

    if self.ui_path.is_dir():
      shutil.rmtree(self.ui_path)
    else:
      self.ui_path.unlink()