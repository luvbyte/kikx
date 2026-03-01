from neko.console import SConsole
from neko.console.page import InputPage

from neko.lib.process import sh

console = SConsole(padding=2)

def print(text):
  console.print(text)

host = InputPage("Enter device IP", placeholder="Type here").display(console).get_input()
port = InputPage("Enter Port", input_type=int, placeholder="Type here").display(console).get_input()
code = InputPage("Pairing Code", input_type=int, placeholder="Type here").display(console).get_input()


console.clear()
print(f"Pairing: [blue]{host}[/blue]:{port} [red]{code}[/red]")

result = sh(f"adb pair {host}:{port} {code}").run()

print(result.text())

