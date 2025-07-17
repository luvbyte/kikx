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

# ----- setting config
def set_config(config: str, value: bool):
  config_map = {
    "block-user-input": "blockUserInput",
    "block-user-clear": "blockUserClear",
    "script-stdout": "setRawOutput",
    "block-kill-task": "blockUserKillTask",
    "script-stdout-parse": "setRawOutputHTML",
  }

  if config not in config_map:
    raise ValueError(f"Error: Invalid '{config}'")

  value_str = "true" if value else "false"
  run_code(f"{config_map[config]}({value_str})")

def set_default_config():
  run_code("setAppDefaultConfig()")

def hide_input_panel():
  run_code("hideInputPanel()")

def set_raw_output_panel(selector):
  run_code(f"setRawOutputPanel('{selector}')")

# -------- Input
# use this method only for input text form user
def ask_input(label: str = "", autohide=True, focus=False, effect=None):
  effect = "null" if effect is None or focus or not autohide else f"'{effect}'"
  run_code(f"askInput(`{label}`, {'true' if focus else 'false'}, {effect})")

  text = input()

  if autohide:
    hide_input_panel()

  return _check_error(text)


def _check_error(text):
  try:
    data = json.loads(text)
    if data.get("event") == "error":
      raise Exception(str(data.get("payload")))
  except (KeyError, json.decoder.JSONDecodeError, TypeError):
    return str(text)
