from lib.utils import dynamic_import

class Plugin:
  def __init__(self, name: str, plugin_path):
    self.module = dynamic_import("plugin_" + name, plugin_path / "main.py", True)
  
  def before_startup(self, kikx_plugin):
    func = getattr(self.module, 'on_before_startup', None)
    if callable(func):
      func(kikx_plugin)
  
  def after_startup(self, kikx_plugin):
    func = getattr(self.module, 'on_after_startup', None)
    if callable(func):
      func(kikx_plugin)
  
  def shutdown(self, *args, **kwargs):
    func = getattr(self.module, 'on_shutdown', None)
    if callable(func):
      func(*args, **kwargs)

class PluginsManager:
  def __init__(self, plugins_manifest):
    self.manifest = plugins_manifest
    self.active_plugins = {}

  def load(self, core):
    for name, plugin in self.manifest.items():
      plugin = Plugin(name, core.config.resolve_path(plugin.path))
      self.active_plugins[name] = plugin

  def before_startup(self, kikx_plugin):
    for plugin in self.active_plugins.values():
      plugin.before_startup(kikx_plugin)

  def after_startup(self, kikx_plugin):
    for plugin in self.active_plugins.values():
      plugin.after_startup(kikx_plugin)

  def shutdown(self, *args, **kwargs):
    for plugin in self.active_plugins.values():
      plugin.shutdown(*args, **kwargs)
