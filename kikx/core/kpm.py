# Kikx Package Manager


class Builder:
  def __init__(self, kikx):
    self.kikx = kikx
  
  def install(self, url):
    pass

def install_app(kikx, uri):
  # 1. load & check manifest.json

  # 2. copy full directory -> apps directory

  # 3. create config file from manifest

  # 4. run setup.sh sctipt

  ...

def uninstall_app(kikx, name):
  # 1. remove app in apps directory

  # 2. remove config in data

  # 3. remove data directory except no_data=True

  ...

