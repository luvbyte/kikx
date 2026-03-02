from fastapi import APIRouter, Request, HTTPException

class ServiceRouter(APIRouter):
  def __init__(self):
    super().__init__()
    self._srv = None
  
  def get_srv(self):
    return self._srv

router = ServiceRouter()

@router.get("/")
async def get_sessions(request: Request):
  srv = router.get_srv()
  client, app = srv.get_client_or_app(request)
  if app and not app.config.system.check("sessions"):
    raise HTTPException(status_code=403, detail="Permission denied")

  core = srv.get_core()

  def sessions_details(client):
    return {
      "id": client.id,
      "apps_count": len(client.running_apps)
    }

  sessions = [sessions_details(v) for k, v in core.clients.items() if k != client.id]
  # ---- fetch client info
  return {
    "sessions": sessions
  }

@router.post("/session/close/{session_id}")
async def close_session(request: Request, session_id: str):
  srv = router.get_srv()
  client, app = srv.get_client_or_app(request)
  
  if app and not app.config.system.check("sessions"):
    raise HTTPException(status_code=403, detail="Permission denied")

  core = srv.get_core()
  
  try:
    result = await core.close_client(session_id)

    return { "res": result }
  except Exception:
    raise HTTPException(status_code=404, detail="Session not found")
