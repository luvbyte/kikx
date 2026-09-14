import os
import shutil

from datetime import datetime
from typing import Any


B1 = r"""
.-. .-')          .-. .-') ) (`-.
\  ( OO )         \  ( OO ) ( OO ).
,--. ,--.  ,-.-') ,--. ,--.(_/.  \_)-.
|  .'   /  |  |OO)|  .'   / \  `.'  /
|      /,  |  |  \|      /,  \     /\
|     ' _) |  |(_/|     ' _)  \   \ |
|  .   \  ,|  |_.'|  .   \   .'    \_)
|  |\   \(_|  |   |  |\   \ /  .'.  \
`--' '--'  `--'   `--' '--''--'   '--'
"""


# ---------------------- Colors
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

  # Bright foreground
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


# ---------------------- Console
class Console:
  def __init__(self, width: int | None = None) -> None:
    self.width: int = width or shutil.get_terminal_size().columns

  # ---------------------- Output
  def clear(self) -> None:
    os.system("cls" if os.name == "nt" else "clear")

  def _time(self) -> str:
    return datetime.now().strftime("%H:%M:%S")

  def color(self, text: Any, *styles) -> str:
    return "".join(styles) + str(text) + Color.RESET

  def newline(self, n: int = 1) -> None:
    self.print("\n" * n, end="")

  def print(self, *args, **kwargs) -> None:
    print(*args, **kwargs)

  def write(self, *text) -> None:
    self.print(*text, end="", flush=True)

  def print_center(self, text: Any) -> None:
    if not isinstance(text, str):
      text = str(text)

    for line in text.split("\n"):
      print(line.center(self.width))

  def title(self, text: str) -> None:
    self.print_center(f"\n[ ======== [ {text} ] ======== ]\n")

  def print_banner(self) -> None:
    self.print_center(B1)

  # ---------------------- Logs
  def log(
    self,
    *text,
    sep: str = " ",
    end: str = "\n",
    timestamp: bool = False,
  ) -> None:
    if timestamp:
      self.print(
        self.color(f"[{self._time()}]", Color.BRIGHT_BLACK),
        end=" ",
      )

    self.print(*text, sep=sep, end=end)

  def info(self, *text) -> None:
    self.print(self.color("[-]", Color.CYAN, Color.BOLD), *text)

  def success(self, *text) -> None:
    self.print(self.color("[+]", Color.GREEN, Color.BOLD), *text)

  def warning(self, *text) -> None:
    self.print(self.color("[*]", Color.YELLOW, Color.BOLD), *text)

  def error(self, *text) -> None:
    self.print(self.color("[x]", Color.RED, Color.BOLD), *text)

  def debug(self, *text) -> None:
    self.print(self.color("[#]", Color.MAGENTA), *text)

  # ---------------------- Input
  def ask(self, prompt: str = "> ", default: Any | None = None) -> str | Any:
    suffix = f" ({default}) " if default is not None else ""
    value = input(self.color(prompt + suffix, Color.GREEN))

    if value == "" and default is not None:
      return default

    return value

  def ask_yes_or_no(self, prompt: str) -> bool:
    while True:
      result = self.ask(prompt + " (Y/n) ").strip().lower()

      if result in ["yes", "y"]:
        return True

      if result in ["no", "n"]:
        return False

      self.print("Please enter yes or no (y/n).")