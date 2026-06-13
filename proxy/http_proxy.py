from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

import state

router = APIRouter()

_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
    "content-encoding", "content-length",
}


@router.api_route("/proxy/{target_url:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def http_proxy(target_url: str, request: Request):
    if not target_url.startswith("http"):
        target_url = "https://" + target_url

    try:
        body = await request.body()
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _HOP_HEADERS and k.lower() != "host"
        }

        resp = await state.http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        )

        size = len(resp.content)
        state.stats["total_bytes"] += size
        state.stats["total_requests"] += 1
        state.hourly_traffic[datetime.now().strftime("%H:00")] += size

        resp_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in _HOP_HEADERS
        }
        return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)

    except Exception as exc:
        state.stats["total_errors"] += 1
        state.error_logs.append({"error": str(exc), "url": target_url, "time": datetime.now().isoformat()})
        raise HTTPException(status_code=502, detail=f"Proxy error: {exc}")
