

# on before start
def on_before_startup(kikx):
  print("Hello from plugin greet :)")

# on after start
def on_shutdown():
  print("greet plugin closed")
