import logging
from pathlib import Path


def setup_logging(logs_path: str = "logs", log_file: str = "kikx.log") -> None:
  log_dir = Path(logs_path)
  log_dir.mkdir(parents=True, exist_ok=True)

  root = logging.getLogger()

  # Don't configure twice
  if root.handlers:
    return

  root.setLevel(logging.DEBUG)

  file_handler = logging.FileHandler(log_dir / log_file, encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(
    logging.Formatter(
      "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
  )

  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)  # or DEBUG if you want
  console_handler.setFormatter(logging.Formatter("%(message)s"))

  root.addHandler(file_handler)
  root.addHandler(console_handler)

  # Silence noisy third-party libraries
  logging.getLogger("httpx").setLevel(logging.WARNING)
  logging.getLogger("multipart").setLevel(logging.WARNING)
  logging.getLogger("python_multipart").setLevel(logging.WARNING)
  # logging.getLogger("uvicorn.access").setLevel(logging.INFO)