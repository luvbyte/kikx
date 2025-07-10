import json


def send_event(event, payload=None):
  print(json.dumps({
    "event": event,
    "payload": payload
  }))

def append(selector, content):
  send_event("append", {
    "element": selector,
    "content": content
  })

def html(selector, content):
  send_event("html", {
    "element": selector,
    "content": content
  })

def text(selector, content):
  send_event("text", {
    "element": selector,
    "content": content
  })

# Run Code
def run_code(code):
  if isinstance(code, list):
    code = ";".join(code)
  send_event("code", code)

# under development dont use yet
def eval(code):
  # TODO: do something for stoping user input
  run_code(f"sendInput({code})")
  return input()

# use this method only for input text form user
def ask_input(label: str = "", autohide=False):
  run_code(f"askInput(`{label}`)")
  text = input()
  if autohide:
    run_code("$taskInputPanel.hide()")

  # if input has error then rise
  try:
    data = json.loads(text)
    if data["event"] == "error":
      raise Exception(str(data["payload"]))
  except (KeyError, json.decoder.JSONDecodeError, TypeError):
    return str(text)

