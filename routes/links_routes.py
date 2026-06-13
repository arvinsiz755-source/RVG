from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
import state
from auth import require_auth
from helpers import generate_uuid, generate_vless_link, get_host, parse_size_to_bytes

router = APIRouter()

@router.post("/api/links")
async def create_link(request: Request, _=Depends(require_auth)):
    body = await request.json()
    uid = generate_uuid()
    async with state.LINKS_LOCK:
        state.LINKS[uid] = {
            "label": body.get("label", "New Link")[:60],
            "limit_bytes": parse_size_to_bytes(float(body.get("limit_value", 0)), body.get("limit_unit", "GB")),
            "used_bytes": 0,
            "created_at": datetime.now().isoformat(),
            "active": True,
        }
    return {"uuid": uid, "vless_link": generate_vless_link(uid, get_host())}

@router.get("/api/links")
async def list_links(_=Depends(require_auth)):
    result = []
    async with state.LINKS_LOCK:
        for uid, data in state.LINKS.items():
            result.append({"uuid": uid, "label": data["label"], "limit_bytes": data["limit_bytes"], "used_bytes": data["used_bytes"], "active": data["active"], "created_at": data["created_at"], "vless_link": generate_vless_link(uid, get_host())})
    return {"links": sorted(result, key=lambda x: x["created_at"], reverse=True)}

@router.delete("/api/links/{uid}")
async def delete_link(uid: str, _=Depends(require_auth)):
    async with state.LINKS_LOCK:
        state.LINKS.pop(uid, None)
    return {"ok": True}
