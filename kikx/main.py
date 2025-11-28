from core.kikx import kikx_app, core
  
def run_server():
  import uvicorn

  server_config = core.config.kikx.server

  config = uvicorn.Config(
    app=kikx_app,
    host=server_config.host,
    port=server_config.port,
    workers=1,
    log_level=server_config.log_level,
  )

  server = uvicorn.Server(config)

  try:
    server.run()
  except KeyboardInterrupt:
    print("Server shutdown requested. Exiting gracefully...")

if __name__ == "__main__":
  run_server()
