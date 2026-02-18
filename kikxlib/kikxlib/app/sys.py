from subprocess import run, PIPE


class ProcessResult:
  def __init__(self, result):
    self.returncode = result.returncode
    self.stdout = result.stdout
    self.stderr = result.stderr

  def output(self):
    return (self.stdout + self.stderr).strip()

# Spawn process
def spawn(command):
  return ProcessResult(run(command, shell=True, stdout=PIPE, stderr=PIPE, text=True))

def whoami():
  return spawn("whoami").output()

def is_sudo():
  return whoami() == "root"

