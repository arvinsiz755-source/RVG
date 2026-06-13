from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends

import state
from auth import require_auth
from helpers import generate_uuid, generate_vless_link, get_host, parse_size_to_bytes

router = APIRouter()


@router.post("/api/links")
async def create_link(request: Request, _=Depends(require_auth)):
    body = await request.json()
    label = (body.get("label") or "لینک جدید").strip()[:60]
    limit_value = float(body.get("limit_value") or 0)
    limit_unit = body.get("limit_unit") or "GB"

    limit_bytes = 0 if limit_value <= 0 else parse_size_to_bytes(limit_value, limit_unit)

    uid = generate_uuid()  # کاملا رندوم
    async with state.LINKS_LOCK:
        state.LINKS[uid] = {
            "label": label,
            "limit_bytes": limit_bytes,
            "used_bytes": 0,
            "created_at": datetime.now().isoformat(),
            "active": True,
        }

    host = get_host()
    return {
        "uuid": uid,
        "label": label,
        "limit_bytes": limit_bytes,
        "used_bytes": 0,
        "active": True,
        "created_at": state.LINKS[uid]["created_at"],
        "vless_link": generate_vless_link(uid, host, remark=f"RVG-{label}"),
    }


@router.get("/api/links")
async def list_links(_=Depends(require_auth)):
    host = get_host()
    result = []
    async with state.LINKS_LOCK:
        for uid, data in state.LINKS.items():
            result.append({
                "uuid": uid,
                "label": data["label"],
                "limit_bytes": data["limit_bytes"],
                "used_bytes": data["used_bytes"],
                "active": data["active"],
                "created_at": data["created_at"],
                "vless_link": generate_vless_link(uid, host, remark=f"RVG-{data['label']}"),
            })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return {"links": result}


@router.patch("/api/links/{uid}")
async def toggle_link(uid: str, request: Request, _=Depends(require_auth)):
    body = await request.json()
    async with state.LINKS_LOCK:
        if uid not in state.LINKS:
            raise HTTPException(status_code=404, detail="link not found")
        if "active" in body:
            state.LINKS[uid]["active"] = bool(body["active"])
        if "limit_value" in body:
            limit_value = float(body.get("limit_value") or 0)
            limit_unit = body.get("limit_unit") or "GB"
            state.LINKS[uid]["limit_bytes"] = 0 if limit_value <= 0 else parse_size_to_bytes(limit_value, limit_unit)
        if "reset_usage" in body and body["reset_usage"]:
            state.LINKS[uid]["used_bytes"] = 0
        if "label" in body:
            state.LINKS[uid]["label"] = str(body["label"])[:60]
    return {"ok": True}


@router.delete("/api/links/{uid}")
async def delete_link(uid: str, _=Depends(require_auth)):
    async with state.LINKS_LOCK:
        state.LINKS.pop(uid, None)
    return {"ok": True}
