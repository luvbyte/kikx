from pydantic import BaseModel, Field
from typing import Any, Literal

from .kikx import SCHEMA

MANAGER_KIKX_SCHEMA = SCHEMA.copy()
MANAGER_KIKX_SCHEMA["services"] = {
  "type": "section",
  "label": "Services (req. Restart)",
  "description": "Optional services configuration",
  "fields": {
    "disabled": {
      "type": "toggle",
      "label": "Disabled Services",
      "description": "Select services to disable",
      "options": [
        {
          "label": "Proxy",
          "value": "proxy",
        },
        {
          "label": "File System",
          "value": "fs",
        },
        {
          "label": "Operating System",
          "value": "os",
        },
        {
          "label": "Key-Value Store",
          "value": "kv",
        },
        {
          "label": "Tasker",
          "value": "tasker",
        }
      ],
    },
  },
  }
