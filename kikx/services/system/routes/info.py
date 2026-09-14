from fastapi import APIRouter, Request


class ServiceRouter(APIRouter):
  def __init__(self) -> None:
    super().__init__()
    self._srv = None

  def get_srv(self):
    return self._srv


router = ServiceRouter()


# ---------------------- Sessions
@router.get("/sessions")
def get_sessions(
  request: Request,
  full: bool = False,
):
  srv = router.get_srv()
  core = srv.get_core()

  client, app = srv.get_client_or_app(request)

  if app and (
    not app.config.system.check("sessions")
    or not app.config.sudo
  ):
    srv.exception(403, "Require 'sessions' and 'sudo' permission")

  def session_details(client):
    if full:
      return client.info()

    return {
      "id": client.id,
      "name": client.name,
      "created_at": client.created_at,
      "apps_count": client.apps_count,
      "active": client.connection.is_connected,
    }

  sessions = [session_details(v) for k, v in core.clients.items() if k != client.id]

  return {
    "sessions": sessions,
  }


@router.get("/session-close")
async def close_session(
  request: Request,
  session_id: str,
):
  srv = router.get_srv()
  _, app = srv.get_client_or_app(request)

  if app and (
    not app.config.system.check("sessions")
    or not app.config.sudo
  ):
    srv.exception(403, "Require 'sessions' and 'sudo' permission")

  core = srv.get_core()

  try:
    await core.close_client(session_id)
    return srv.ok()
  except Exception:
    srv.exception(404, "Session not found")


# ---------------------- Apps
@router.get("/apps-list")
def get_installed_apps(
  request: Request,
  meta: bool = False,
):
  srv = router.get_srv()

  srv.get_client_or_app(request)
  core = srv.get_core()

  return [
    app["name"] if not meta else app
    for app in core.get_installed_apps()
  ]


@router.get("/app")
def get_app_info(request: Request):
  srv = router.get_srv()
  _, app = srv.get_client_app(request)

  return app.info()


# ---------------------- Client
@router.get("/client")
def get_client_info(request: Request):
  srv = router.get_srv()
  client = srv.get_client(request)

  return client.info()


# ---------------------- Kikx
@router.get("/kikx")
def get_kikx_info(request: Request):
  srv = router.get_srv()

  srv.get_client_or_app(request)

  core = srv.get_core()

  return {
    "version": core.version,
    "author": core.author,
    "dev_mode": core.is_dev_mode,
  }