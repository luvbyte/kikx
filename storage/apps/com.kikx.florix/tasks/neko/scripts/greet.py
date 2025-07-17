from neko.lib.console import Console


banner = r"""
🟨🟨🟨🟨🟨🟨🟨🟨
🟨💗💗🟨🟨💗💗🟨
💗💗💗💗💗💗💗💗
💗💗💗💗💗💗💗💗
💗💗💗💗💗💗💗💗
🟨💗💗💗💗💗💗🟨
🟨🟨💗💗💗💗🟨🟨
🟨🟨🟨💗💗🟨🟨🟨 
"""

console = Console()

def start():
  #sleep(3)
  name = console.input("Type your name")

  console.pre_center(f"Hello {name} this is for you", effect="fadeIn")
  #sleep(2)
  console.pre_center(banner, effect="fadeIn")
