from cli.cmd import CmdBase
from core.core import Core

from .modules.apps import Apps

class CLI(CmdBase):
  def __init__(self):
    super().__init__(Core("../tempfs", True))

    self.prompt = "| "

    self.modules = {
      "apps": Apps(self.core)
    }

  def do_use(self, line):
    module = self.modules.get(str(line))
    if not module:
      self.scr.error("Module not found")
      return

    module.init()
    module.cmdloop()

  def banner(self):
    self.scr.title("CLI")

  def start(self):
    self.banner()
    self.cmdloop()

# ------------->

