from nekolib import js, panel
from nekolib.process import sh
from subprocess import PIPE

panel.clear(True)
js.run_code("blockUserClear(false)")
js.run_code("setRawOutput()")

while True:
  input_text = js.ask_input("Enter command", autohide=False).strip()

  if input_text == "exit":
    exit()
  elif input_text == "clear":
    js.run_code("clearPanel()")
  else:
    process = sh(input_text).pipe(stderr=PIPE)
    if process.returncode != 0: # success
      print(f"Error ({process.returncode}): {process.error()}")

