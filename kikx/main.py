

def main() -> None:
  from core.global_config import GlobalConfig
  
  gconfig = GlobalConfig()

  print("Starting kikx...")

  gconfig.kikx.dev_mode = False

  from kikx import kikx_app, core
  import uvicorn

  server_config = core.config.kikx.server

  config = uvicorn.Config(
    app=kikx_app,
    host=server_config.host,
    port=server_config.port,
    workers=1,
    log_level=server_config.log_level,
    timeout_graceful_shutdown=server_config.timeout_graceful_shutdown
  )

  core.scr.print_banner()
  core.scr.title(f"ᥫ᭡ {core.author} - v{core.version}")

  server = uvicorn.Server(config)

  try:
    server.run()
  except KeyboardInterrupt:
    core.scr.print("\nBye :)")


if __name__ == "__main__":
  main()
