from core.core import app, core


if __name__ == "__main__":
  import uvicorn
  server_config = core.config.kikx.server
  config = uvicorn.Config(
    app, host=server_config.host,
    port=server_config.port,
    workers=1,
    log_level=server_config.log_level
  )
  try:
    uvicorn.Server(config).run()
  except KeyboardInterrupt:
    pass

