from datetime import datetime

from fastapi import APIRouter, Depends

import state
from auth import require_auth
from helpers import get_host

router = APIRouter()


@router.get("/")
async def root():
    return {
        "service": "RVG Gateway – codebox",
        "version": "6.0",
        "status": "active",
        "channel": "https://t.me/CodeBoxo",
        "host": get_host(),
    }


@router.get("/health")
async def health():
    return {"status": "ok", "connections": len(state.connections), "uptime": state.uptime()}


@router.get("/stats")
async def get_stats(_=Depends(require_auth)):
    now = datetime.now()
    return {
        "active_connections": len(state.connections),
        "total_traffic_mb": round(state.stats["total_bytes"] / (1024 * 1024), 2),
        "total_requests": state.stats["total_requests"],
        "total_errors": state.stats["total_errors"],
        "uptime": state.uptime(),
        "timestamp": now.isoformat(),
        "hourly": dict(state.hourly_traffic),
        "recent_errors": list(state.error_logs)[-10:],
        "links_count": len(state.LINKS),
    }
