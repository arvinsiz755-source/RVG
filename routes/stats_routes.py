from datetime import datetime
from fastapi import APIRouter, Depends
import state
from auth import require_auth

router = APIRouter()

@router.get("/stats")
async def get_stats(_=Depends(require_auth)):
    return {
        "active_connections": len(state.connections),
        "total_traffic_mb": round(state.stats["total_bytes"] / 1048576, 2),
        "total_requests": state.stats["total_requests"],
        "total_errors": state.stats["total_errors"],
        "uptime": state.uptime(),
        "hourly": dict(state.hourly_traffic),
        "links_count": len(state.LINKS),
    }
