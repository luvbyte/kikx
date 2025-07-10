import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
  os.makedirs(log_dir)

# Log format
log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

# Function to create and configure a logger with a dynamic name
def get_logger(name: str):
  logger = logging.getLogger(name)
  logger.setLevel(logging.INFO)

  # Avoid adding multiple handlers (prevents duplicate logs)
  if not logger.hasHandlers():
    # Console handler (logs to terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # File handler (logs to logs/module_name.log)
    #log_file = os.path.join(log_dir, f"{name}.log")
    #file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    #file_handler.setFormatter(log_format)
    #logger.addHandler(file_handler)

  return logger

