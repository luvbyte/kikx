from subprocess import Popen, PIPE
import sys
from os import getcwd


class Process:
  def __init__(self, proc):
    self._process = proc
    self._process.wait()
    
  def output(self):
    return self._process.stdout.read().decode('utf-8').strip()
  
  def error(self):
    return self._process.stderr.read().decode('utf-8').strip()

  @property
  def returncode(self):
    return self._process.returncode

class ProcessBuilder:
  def __init__(self, cmd):
    self.cmd = cmd
    self.stdout, self.stdin, self.stderr = (PIPE, PIPE, PIPE)
    self.cwd = getcwd()
    
    self.shell = True
    
  def pipe(self, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr
    return self.run()
  
  def run(self):
    return Process(Popen(self.cmd, cwd=self.cwd, shell=self.shell, stdin=self.stdin, stdout=self.stdout, stderr=self.stderr))
 
def sh(cmd):
  return ProcessBuilder(cmd)
