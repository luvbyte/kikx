import os
import shutil
from typing import Any
from datetime import datetime


B1 = r"""
.-. .-')          .-. .-') ) (`-.      
\  ( OO )         \  ( OO ) ( OO ).    
,--. ,--.  ,-.-') ,--. ,--.(_/.  \_)-. 
|  .'   /  |  |OO)|  .'   / \  `.'  /  
|      /,  |  |  \|      /,  \     /\  
|     ' _) |  |(_/|     ' _)  \   \ |  
|  .   \  ,|  |_.'|  .   \   .'    \_) 
|  |\   \(_|  |   |  |\   \ /  .'.  \  
`--' '--'  `--'   `--' '--''--'   '--' """

class Color:
  RESET = "\033[0m"

  # Styles
  BOLD = "\033[1m"
  DIM = "\033[2m"
  ITALIC = "\033[3m"
  UNDERLINE = "\033[4m"

  # Foreground
  BLACK = "\033[30m"
  RED = "\033[31m"
  GREEN = "\033[32m"
  YELLOW = "\033[33m"
  BLUE = "\033[34m"
  MAGENTA = "\033[35m"
  CYAN = "\033[36m"
  WHITE = "\033[37m"

  # Bright Foreground
  BRIGHT_BLACK = "\033[90m"
  BRIGHT_RED = "\033[91m"
  BRIGHT_GREEN = "\033[92m"
  BRIGHT_YELLOW = "\033[93m"
  BRIGHT_BLUE = "\033[94m"
  BRIGHT_MAGENTA = "\033[95m"
  BRIGHT_CYAN = "\033[96m"
  BRIGHT_WHITE = "\033[97m"

  # Background
  BG_RED = "\033[41m"
  BG_GREEN = "\033[42m"
  BG_BLUE = "\033[44m"
  BG_YELLOW = "\033[43m"


class Console:
  def __init__(self, width=None) -> None:
    # Auto-detect terminal width if not provided
    self.width = width or shutil.get_terminal_size().columns

  # ------------ utils
  def clear(self):
    os.system("cls" if os.name == "nt" else "clear")

  def _time(self):
    return datetime.now().strftime("%H:%M:%S")

  def color(self, text, *styles):
    return "".join(styles) + str(text) + Color.RESET

  def newline(self, n=1):
    self.print("\n" * n, end="")
  
  def exit(self, code=0):
    exit(code)

  # ------------ print
  def print(self, *args, **kwargs) -> None:
    print(*args, **kwargs)

  def write(self, *text):
    self.print(*text, end="", flush=True)

  def print_center(self, text: Any) -> None:
    if not isinstance(text, str):
      text = str(text)

    lines = text.split("\n")
    for line in lines:
      print(line.center(self.width))

  def title(self, text: str):
    self.print_center(f"\n[ ======== [ {text} ] ======== ]\n")

  def print_banner(self) -> None:
    self.print_center(B1)

  # ------------ logging
  def log(self, *text, sep=" ", end="\n", timestamp=False):
    if timestamp:
      self.print(self.color(f"[{self._time()}]", Color.BRIGHT_BLACK), end=" ")
    self.print(*text, sep=sep, end=end)
  
  def info(self, *text):
    self.print(self.color("[-]", Color.CYAN, Color.BOLD), *text)

  def success(self, *text):
    self.print(self.color("[+]", Color.GREEN, Color.BOLD), *text)

  def warning(self, *text):
    self.print(self.color("[*]", Color.YELLOW, Color.BOLD), *text)

  def error(self, *text):
    self.print(self.color("[x]", Color.RED, Color.BOLD), *text)

  def debug(self, *text):
    self.print(self.color("[#]", Color.MAGENTA), *text)

  # ------------ Input
  def ask(self, prompt="> ", default=None):
    value = input(self.color(prompt + (f" ({default}) " if default is not None else ""), Color.GREEN))
    if value == "" and default is not None:
      return default
    return value
  
  def ask_yes_or_no(self, prompt):
    while True:
      result = self.ask(prompt + " (Y/n) ").strip().lower()
      if result in ["yes", "y"]:
        return True
      elif result in ["no", "n"]:
        return False
      else:
        self.print("Please enter yes or no (y/n).")
