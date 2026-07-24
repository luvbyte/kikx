from cmd2 import Cmd


class CmdBase(Cmd):
  def __init__(self, core):
    super().__init__()

    self.core = core

  @property
  def scr(self):
    return self.core.scr

  def do_clear(self, _):
    self.scr.clear()
