import sys
from os import getcwd
from subprocess import Popen, PIPE



class Process:
  def __init__(self, proc: Popen) -> None:
    """
    Wraps a subprocess.Popen instance and waits for it to complete.
    """
    self._process = proc
    self._process.wait()

  def output(self) -> str:
    """
    Returns the process output (stdout) as a decoded, stripped string.
    """
    if self._process.stdout:
      output = self._process.stdout.read().decode("utf-8").strip()
      return output
    return ""

  @property
  def returncode(self) -> int:
    """
    Return the process exit code.
    """
    return self._process.returncode


class ProcessBuilder:
  def __init__(self, cmd: str) -> None:
    """
    A builder for configuring and running shell processes.
    """
    self.cmd: str = cmd
    self.stdin = PIPE
    self.stdout = PIPE
    self.stderr = PIPE
    self.cwd: str = getcwd()
    self.shell: bool = True

  def pipe(self) -> Process:
    """
    Run the command and capture stdout/stderr via pipes.
    """
    return self._run()

  def run(self, capture_output: bool = True) -> Process:
    """
    Run the command. If capture_output is False, inherit sys stdio.
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
  Entry point for building and running a shell process.
  """
  return ProcessBuilder(cmd)
