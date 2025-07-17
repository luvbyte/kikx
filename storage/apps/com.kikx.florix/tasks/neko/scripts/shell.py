from neko.lib import js, panel
from neko.lib.process import sh
from subprocess import PIPE

js.set_config("block-user-clear", False)
js.set_config("block-user-input", False)

while True:
  input_text = js.ask_input("Enter command", autohide=False, effect="fadeIn").strip()

  if input_text == "exit":
    break
  elif input_text == "clear":
    js.run_code("clearPanel()")
  else:
    process = sh(input_text).pipe(stderr=PIPE)
    if process.returncode != 0: # success
      print(f"Error ({process.returncode}): {process.error()}")

