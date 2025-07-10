

def get_request_id(request):
  if "kikx-app-id" in request:
    return 0, request.get("kikx-app-id")
  elif "kikx-client-id" in request:
    return 1, request.get("kikx-client-id")
  else:
    raise Exception("Require 'kikx-[app|client]-id'")


