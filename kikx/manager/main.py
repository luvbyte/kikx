import os

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from lib.utils import file_response, joinpath, import_relative_module

from .manager import KikxManager


manager = KikxManager()


# Auto register routes
for file in os.listdir("manager/routes"):
  if file.endswith(".py") and file not in ("__init__.py",):
    module_name = file[:-3]  # remove .py

    module = import_relative_module(f"manager.routes.{module_name}", module_name)

    # attach router if exists
    if hasattr(module, "router"):
      manager.router.include_router(getattr(module, "router"), prefix=f"/{module_name}", tags=[module_name.capitalize()])


# Websocket router
@manager.router.websocket("/client")
async def websocket_client_endpoint(websocket: WebSocket):
  await websocket.accept()
  
  manager.on_connect(websocket)

  while True:
    try:
      data = await websocket.receive_json()
      await manager.on_data(websocket, data)
    except WebSocketDisconnect:
      break
    except RuntimeError:
      break
    except Exception:
      break

  # Try closing
  try:
    await websocket.close()
  except Exception:
    pass
  finally:
    manager.on_disconnect(websocket)



