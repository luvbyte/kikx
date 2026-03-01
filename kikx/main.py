from core.kikx import kikx_app, core
from core.console import Console


def run_server():
  import uvicorn

  core._dev_mode = False

  server_config = core.config.kikx.server

  config = uvicorn.Config(
    app=kikx_app,
    host=server_config.host,
    port=server_config.port,
    workers=1,
    log_level=server_config.log_level,
  )
  
  core.scr.print_banner(core.version, core.author)

  server = uvicorn.Server(config)

  try:
    server.run()
  except KeyboardInterrupt:
    print("Bye :)")

if __name__ == "__main__":
  run_server()
