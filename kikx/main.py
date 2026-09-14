
def main() -> None:
  from core.global_config import GlobalConfig

  gconfig = GlobalConfig()

  print("Starting kikx...")

  gconfig.kikx.dev_mode = False

  from kikx import kikx_app
  import uvicorn

  server_config = kikx_app.core.config.server

  config = uvicorn.Config(
    app=kikx_app,
    host=server_config.host,
    port=server_config.port,
    workers=1,
    log_level=server_config.log_level,
    access_log=server_config.access_log,
    timeout_graceful_shutdown=server_config.timeout
  )

  kikx_app.core.scr.print_banner()
  kikx_app.core.scr.title(f"ᥫ᭡ {kikx_app.core.author} - v{kikx_app.core.version}")

  server = uvicorn.Server(config)

  try:
    server.run()
  except KeyboardInterrupt:
    pass
  except Exception:
    raise


if __name__ == "__main__":
  main()