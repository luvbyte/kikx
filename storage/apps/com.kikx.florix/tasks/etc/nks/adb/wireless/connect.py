from neko.console import SConsole
from neko.console.page import InputPage

from neko.lib.process import sh

console = SConsole(padding=2)

def print(text):
  console.print(text)

host = InputPage("Enter device IP", placeholder="Type here").display(console).get_input()
port = InputPage("Enter Port", input_type=int, placeholder="Type here").display(console).get_input()


console.clear()
print(f"Connecting: [blue]{host}[/blue]:{port}")

result = sh(f"adb connect {host}:{port}").run()

print(result.text())
