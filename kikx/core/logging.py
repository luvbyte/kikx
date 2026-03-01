import os
import logging


class Logger:
  def __init__(self, name: str = "kikx", log_file: str = "kikx.log"):
    self.logger = logging.getLogger(name)
    self.logger.setLevel(logging.DEBUG)
    self.logger.propagate = False  # Prevent duplicate logs

    # Avoid adding handlers multiple times
    if not self.logger.handlers:
      # Create logs directory if not exists
      os.makedirs("logs", exist_ok=True)
      log_path = os.path.join("logs", log_file)

      # File Handler (WITH timestamp)
      file_handler = logging.FileHandler(log_path)
      file_handler.setLevel(logging.DEBUG)
      file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
      )
      file_handler.setFormatter(file_formatter)

      # Console Handler (WITHOUT timestamp)
      console_handler = logging.StreamHandler()
      console_handler.setLevel(logging.DEBUG)
      console_formatter = logging.Formatter("%(message)s")
      console_handler.setFormatter(console_formatter)

      # Add handlers
      self.logger.addHandler(file_handler)
      self.logger.addHandler(console_handler)

  def get_logger(self):
    return self.logger

