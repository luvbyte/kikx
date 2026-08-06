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
  def __init__(self, width: int | None = None) -> None:
    # Auto-detect terminal width if not provided
    self.width: int = width or shutil.get_terminal_size().columns

  # Clear screen
  def clear(self) -> None:
    os.system("cls" if os.name == "nt" else "clear")

  # Time
  def _time(self) -> Any:
    return datetime.now().strftime("%H:%M:%S")

  # Color Text
  def color(self, text: Any, *styles) -> str:
    return "".join(styles) + str(text) + Color.RESET

  # Print new lines
  def newline(self, n: int = 1) -> None:
    self.print("\n" * n, end="")

  # Print
  def print(self, *args, **kwargs) -> None:
    print(*args, **kwargs)

  # Write
  def write(self, *text) -> None:
    self.print(*text, end="", flush=True)

  # Print text center
  def print_center(self, text: Any) -> None:
    if not isinstance(text, str):
      text = str(text)

    lines = text.split("\n")
    for line in lines:
      print(line.center(self.width))
  
  # Print center title
  def title(self, text: str) -> None:
    self.print_center(f"\n[ ======== [ {text} ] ======== ]\n")

  # Print banner
  def print_banner(self) -> None:
    self.print_center(B1)

  # Log
  def log(self, *text, sep: str = " ", end: str = "\n", timestamp: bool = False) -> None:
    if timestamp:
      self.print(self.color(f"[{self._time()}]", Color.BRIGHT_BLACK), end=" ")
    self.print(*text, sep=sep, end=end)
  
  # Log Info
  def info(self, *text) -> None:
    self.print(self.color("[-]", Color.CYAN, Color.BOLD), *text)

  # Log Success
  def success(self, *text) -> None:
    self.print(self.color("[+]", Color.GREEN, Color.BOLD), *text)

  # Log Warning
  def warning(self, *text) -> None:
    self.print(self.color("[*]", Color.YELLOW, Color.BOLD), *text)

  # Log Error
  def error(self, *text) -> None:
    self.print(self.color("[x]", Color.RED, Color.BOLD), *text)

  # Log Debug
  def debug(self, *text) -> None:
    self.print(self.color("[#]", Color.MAGENTA), *text)

  # Ask Input
  def ask(self, prompt: str = "> ", default: Any | None = None) -> str | Any:
    value = input(self.color(prompt + (f" ({default}) " if default is not None else ""), Color.GREEN))
    if value == "" and default is not None:
      return default
    return value
  
  # Ask Input (y/n)
  def ask_yes_or_no(self, prompt: str) -> bool:
    while True:
      result = self.ask(prompt + " (Y/n) ").strip().lower()
      if result in ["yes", "y"]:
        return True
      elif result in ["no", "n"]:
        return False
      else:
        self.print("Please enter yes or no (y/n).")
