import sys
import platform
import pytest

from lib import process as pu


def test_pipe_output_basic_command():
  proc = pu.sh("echo Hello, World!").pipe()
  assert proc.returncode == 0
  assert proc.output() == "Hello, World!"

@pytest.mark.skipif(platform.system() == "Windows", reason="Unix-only test")
def test_pipe_unix_command():
  proc = pu.sh("ls /").pipe()
  assert proc.returncode == 0
  assert "bin" in proc.output().split("\n")

@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
def test_pipe_windows_command():
  proc = pu.sh("dir").pipe()
  assert proc.returncode == 0
  assert "Volume" in proc.output() or "Directory" in proc.output()

