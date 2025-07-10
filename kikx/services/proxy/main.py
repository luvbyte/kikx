from fastapi import Request, HTTPException, Query, Response
import httpx

from lib.service import create_service


srv = create_service(__file__)

def check_app_permission(app):
  if "proxy" not in app.config.services:
    srv.exception(401, "Permission Denied: 'proxy' not found!!?")

async def forward_request(method: str, request: Request, target_url: str):
  """Forwards the request to the target URL while adding CORS headers."""
  headers = dict(request.headers)

  client, app = srv.get_client_or_app(request)
  if app:
    headers.pop("kikx-app-id")
    check_app_permission(app)
  else:
    headers.pop("kikx-client-id")

  if not target_url:
    raise HTTPException(status_code=400, detail="Missing target URL in query parameter")

  headers.pop("host", None)
  # headers = {key: value for key, value in request.headers.items() if key.lower() != "host"}

  try:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
      if method in ["GET", "DELETE"]:
        response = await client.request(method, target_url, headers=headers, params=request.query_params)
      else:
        body = await request.body()
        response = await client.request(method, target_url, headers=headers, content=body)

    # Forward all headers except 'transfer-encoding' to avoid issues
    response_headers = {k: v for k, v in response.headers.items() if k.lower() != "transfer-encoding"}
    # print(response_headers.items())

    # 🔥 Manually add CORS headers to prevent browser blocking
    response_headers["Access-Control-Allow-Origin"] = "null"  # Allow all domains (change if needed)
    response_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response_headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response_headers["Access-Control-Allow-Credentials"] = "true"

    return Response(
      content=response.content, 
      status_code=response.status_code, 
      media_type=response.headers.get("content-type", "application/octet-stream"),
      headers=response_headers
    )

  except httpx.TimeoutException:
    raise HTTPException(status_code=504, detail="Request to target server timed out")

  except httpx.RequestError:
    raise HTTPException(status_code=502, detail="Failed to connect to target server")

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@srv.router.get("/")
async def proxy_get(request: Request, url: str = Query(...)):
  return await forward_request("GET", request, url)

@srv.router.post("/")
async def proxy_post(request: Request, url: str = Query(...)):
  return await forward_request("POST", request, url)

@srv.router.put("/")
async def proxy_put(request: Request, url: str = Query(...)):
  return await forward_request("PUT", request, url)

@srv.router.delete("/")
async def proxy_delete(request: Request, url: str = Query(...)):
  return await forward_request("DELETE", request, url)

@srv.router.patch("/")
async def proxy_patch(request: Request, url: str = Query(...)):
  return await forward_request("PATCH", request, url)

