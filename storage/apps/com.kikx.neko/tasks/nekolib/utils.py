import bleach

def safe_code(html):
  if isinstance(html, list):
    return [safe_code(code) for code in html]
  elif isinstance(html, str):
    return bleach.clean(html)
  else:
    raise Exception("Unknown type")

def get_item(lst, index, default=None):
  try:
    return lst[index]
  except IndexError:
    return default
