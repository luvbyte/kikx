from fastapi import APIRouter, Request


class ServiceRouter(APIRouter):
  def __init__(self):
    super().__init__(self)
    # will be update on include
    self.srv = None

router = APIRouter()

@router.get("/")
async def info(request: Request):
  srv = router.srv

  client, app = srv.get_client_app(request)
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
  srv = router.srv

  srv.get_client_or_app(request)
  core = router.srv.get_core()
  try:
    await core.close_client(session_id)
  except Exception as e:
    router.srv.exception(detail=str(e))