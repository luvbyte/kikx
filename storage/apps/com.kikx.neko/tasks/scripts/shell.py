from nekolib import js, panel
from nekolib.process import sh


panel.clear(True)
js.run_code("setRawOutput()")
js.run_code("blockUserClear(false)")

while True:
  input_text = js.ask_input("Enter command", autohide=False).strip()
  if input_text == "exit":
    exit()
  else:
    sh(input_text).pipe()

