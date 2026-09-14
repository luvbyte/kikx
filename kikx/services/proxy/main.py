import logging

import httpx

from fastapi import Request, Response

from lib.service import create_service


logger = logging.getLogger(__name__)

srv = create_service(__file__)


# ---------------------- Forward
async def _forward_request(
  method: str,
  request: Request,
  headers: dict,
):
  """Forward the request to the target URL and add CORS headers."""
  params = dict(request.query_params)

  target_url = params.pop("__proxy_target", None)

  if target_url is None:
    srv.exception(400, "Missing target URL in query parameter")

  try:
    async with httpx.AsyncClient(
      timeout=30,
      follow_redirects=True,
    ) as client:
      if method in {"GET", "DELETE"}:
        response = await client.request(
          method,
          target_url,
          headers=headers,
          params=params,
        )
      else:
        body = await request.body()

        response = await client.request(
          method,
          target_url,
          headers=headers,
          params=params,
          content=body,
        )

    # Don't forward transfer-encoding because httpx handles it.
    response_headers = {
      key: value
      for key, value in response.headers.items()
      if key.lower() != "transfer-encoding"
    }

    # Add CORS headers for browser requests.
    response_headers.update({
      "Access-Control-Allow-Origin": "null",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
      "Access-Control-Allow-Credentials": "true",
    })

    return Response(
      content=response.content,
      status_code=response.status_code,
      media_type=response.headers.get(
        "content-type",
        "application/octet-stream",
      ),
      headers=response_headers,
    )

  except httpx.TimeoutException:
    srv.exception(504, "Request to target server timed out")

  except httpx.RequestError:
    srv.exception(502, "Failed to connect to target server")

  except Exception:
    logger.exception("Proxy request failed")
    srv.exception(500, "Internal server error")


# ---------------------- Request
async def forward_request(
  method: str,
  request: Request,
):
  client, app = srv.get_client_or_app(request)

  headers = dict(request.headers)

  if app:
    if not app.config.has_service("proxy"):
      srv.exception(403, "Service 'proxy' not found in config")

    headers.pop("kikx-app-id", None)
  else:
    headers.pop("kikx-client-id", None)

  # Let the target server handle its own host header.
  headers.pop("host", None)

  return await _forward_request(method, request, headers)


# ---------------------- Routes
@srv.router.get("/")
async def proxy_get(request: Request):
  return await forward_request("GET", request)


@srv.router.post("/")
async def proxy_post(request: Request):
  return await forward_request("POST", request)


@srv.router.put("/")
async def proxy_put(request: Request):
  return await forward_request("PUT", request)


@srv.router.delete("/")
async def proxy_delete(request: Request):
  return await forward_request("DELETE", request)


@srv.router.patch("/")
async def proxy_patch(request: Request):
  return await forward_request("PATCH", request)