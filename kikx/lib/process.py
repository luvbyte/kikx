from subprocess import Popen, PIPE
from os import getcwd
import sys


class Process:
  def __init__(self, proc: Popen):
    self._process = proc
    self._process.wait()

  def output(self) -> str:
    """
    Returns the process output (stdout) as a decoded, stripped string.
    """
    if self._process.stdout:
      return self._process.stdout.read().decode("utf-8").strip()
    return ""

  @property
  def returncode(self) -> int:
    return self._process.returncode


class ProcessBuilder:
  def __init__(self, cmd: str):
    self.cmd = cmd
    self.stdin = PIPE
    self.stdout = PIPE
    self.stderr = PIPE
    self.cwd = getcwd()
    self.shell = True

  def pipe(self) -> Process:
    """
    Run the command and capture the output via pipes.
    """
    return self._run()

  def run(self, capture_output: bool = True) -> Process:
    """
    Run the command. If capture_output is False, inherit std IO streams.
    """
    if not capture_output:
      self.stdin = sys.stdin
      self.stdout = sys.stdout
      self.stderr = sys.stderr
    return self._run()

  def _run(self) -> Process:
    proc = Popen(
      self.cmd,
      cwd=self.cwd,
      shell=self.shell,
      stdin=self.stdin,
      stdout=self.stdout,
      stderr=self.stderr,
    )
    return Process(proc)


def sh(cmd: str) -> ProcessBuilder:
  """
  Entry point for building a shell process.
  """
  return ProcessBuilder(cmd)

