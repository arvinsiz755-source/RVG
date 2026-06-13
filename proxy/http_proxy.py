from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import Response
import state

router = APIRouter()
_HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "te", "transfer-encoding", "upgrade"}

@router.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"])
async def proxy(path: str, request: Request):
    url = f"https://{path}" if not path.startswith("http") else "https://" + path
    try:
        body = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_HEADERS and k.lower() != "host"}
        resp = await state.http_client.request(request.method, url, headers=headers, content=body)
        state.stats["total_bytes"] += len(resp.content)
        state.stats["total_requests"] += 1
        return Response(content=resp.content, status_code=resp.status_code, headers={k: v for k, v in resp.headers.items() if k.lower() not in _HOP_HEADERS})
    except Exception as e:
        state.stats["total_errors"] += 1
        return Response(content=str(e), status_code=502)
