import logging
from pathlib import Path
from typing import Any

from lib.utils import dynamic_import

logger = logging.getLogger(__name__)


class Plugin:
  """Represents a single dynamically loaded plugin."""
  def __init__(self, name: str, plugin_path: Path):
    self.name = name
    self.module = dynamic_import(f"plugin_{name}", plugin_path / "main.py", True)
    logger.info(f"Plugin '{name}' loaded from {plugin_path}")

  def before_startup(self, kikx_plugin: Any) -> None:
    func = getattr(self.module, 'on_before_startup', None)
    if callable(func):
      logger.debug(f"Calling before_startup for plugin '{self.name}'")
      func(kikx_plugin)

  def after_startup(self, kikx_plugin: Any) -> None:
    func = getattr(self.module, 'on_after_startup', None)
    if callable(func):
      logger.debug(f"Calling after_startup for plugin '{self.name}'")
      func(kikx_plugin)

  def shutdown(self, *args, **kwargs) -> None:
    func = getattr(self.module, 'on_shutdown', None)
    if callable(func):
      logger.debug(f"Calling shutdown for plugin '{self.name}'")
      func(*args, **kwargs)


class PluginsManager:
  """Manages loading and lifecycle of all plugins."""
  def __init__(self, plugins_manifest: dict[str, Any]):
    self.manifest = plugins_manifest
    self.active_plugins: dict[str, Plugin] = {}

  def load(self, core: Any) -> None:
    for name, plugin_cfg in self.manifest.items():
      plugin_path = core.config.resolve_path(plugin_cfg.path)
      plugin = Plugin(name, plugin_path)
      self.active_plugins[name] = plugin
    logger.info(f"Loaded {len(self.active_plugins)} plugins")

  def before_startup(self, kikx_plugin: Any) -> None:
    for plugin in self.active_plugins.values():
      plugin.before_startup(kikx_plugin)

  def after_startup(self, kikx_plugin: Any) -> None:
    for plugin in self.active_plugins.values():
      plugin.after_startup(kikx_plugin)

  def shutdown(self, *args, **kwargs) -> None:
    for plugin in self.active_plugins.values():
      plugin.shutdown(*args, **kwargs)
