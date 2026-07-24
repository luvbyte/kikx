from fastapi import APIRouter, Request


class ServiceRouter(APIRouter):
  def __init__(self):
    super().__init__()
    self._srv = None
  
  def get_srv(self):
    return self._srv

router = ServiceRouter()

@router.get("/sessions")
async def get_sessions(request: Request):
  srv = router.get_srv()
  core = srv.get_core()

  client, app = srv.get_client_or_app(request)
  if app and (not app.config.system.check("sessions") or not app.config.sudo):
    srv.exception(403, "Require 'sessions' and 'sudo' permission")

  def sessions_details(client):
    return {
      "id": client.id,
      "apps_count": len(client.running_apps)
    }

  sessions = [sessions_details(v) for k, v in core.clients.items() if k != client.id]
  # ---- fetch client info
  return {
    "sessions": sessions,
  }

@router.post("/session/close/{session_id}")
async def close_session(request: Request, session_id: str):
  srv = router.get_srv()
  _, app = srv.get_client_or_app(request)
  
  if app and (not app.config.system.check("sessions") or not app.config.sudo):
    srv.exception(403, "Require 'sessions' and 'sudo' permission")

  core = srv.get_core()

  try:
    result = await core.close_client(session_id)

    return { "res": result }
  except Exception:
    srv.exception(404, "Session not found")

@router.get("/app")
def get_app_info(request: Request):
  srv = router.get_srv()
  _, app = srv.get_client_app(request)

  return app.info()

@router.get("/client")
def get_client_info(request: Request):
  srv = router.get_srv()
  client = srv.get_client(request)

  return client.info()

@router.get("/apps-list")
async def get_installed_apps(request: Request, extra: bool = False):
  srv = router.get_srv()
  # Restrict
  srv.get_client_or_app(request)
  core = srv.get_core()
  
  system_apps = core.get_admin_apps_list()

  return [ m["name"] if not extra else { **m, "system": m["name"] in system_apps } for m in core.get_installed_apps() ]

@router.get("/kikx")
def get_kikx_info(request: Request):
  srv = router.get_srv()
  # Restrict
  srv.get_client_or_app(request)
  core = srv.get_core()
  
  return { 
    "version": core.version,
    "author": core.author,
    "dev_mode": core.is_dev_mode
  }

