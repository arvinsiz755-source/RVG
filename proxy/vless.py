import asyncio
import secrets
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import state

router = APIRouter()
RELAY_BUF = 256 * 1024
_quota_cache = {}

async def check_quota(uid: str, extra: int) -> bool:
    import time
    now = time.time()
    if uid in _quota_cache and (now - _quota_cache[uid][1]) < 0.1:
        return _quota_cache[uid][0]
    async with state.LINKS_LOCK:
        link = state.LINKS.get(uid)
        if not link or not link["active"]:
            res = False
        elif link["limit_bytes"] == 0:
            res = True
        else:
            res = (link["used_bytes"] + extra) <= link["limit_bytes"]
    _quota_cache[uid] = (res, now)
    return res

@router.websocket("/ws/{uuid}")
async def ws_tunnel(websocket: WebSocket, uuid: str):
    await websocket.accept()
    conn_id = secrets.token_urlsafe(8)
    state.connections[conn_id] = {"uuid": uuid, "connected_at": datetime.now().isoformat(), "bytes": 0}
    writer = None
    try:
        if not await check_quota(uuid, 0):
            await websocket.close(code=1008)
            return
        msg = await asyncio.wait_for(websocket.receive(), timeout=10)
        if msg["type"] == "websocket.disconnect":
            return
        chunk = msg.get("bytes") or (msg.get("text", "").encode())
        if not chunk:
            return
        # Parse header simplified
        pos = 1
        pos += 16
        addon = chunk[pos]
        pos += 1 + addon
        pos += 1
        port = int.from_bytes(chunk[pos:pos+2], "big")
        pos += 2
        atype = chunk[pos]
        pos += 1
        if atype == 1:
            addr = f"{chunk[pos]}.{chunk[pos+1]}.{chunk[pos+2]}.{chunk[pos+3]}"
            pos += 4
        elif atype == 2:
            dlen = chunk[pos]
            pos += 1
            addr = chunk[pos:pos+dlen].decode()
            pos += dlen
        else:
            addr = "::1"
        payload = chunk[pos:]
        size = len(chunk)
        state.stats["total_bytes"] += size
        state.stats["total_requests"] += 1
        async with state.LINKS_LOCK:
            if uuid in state.LINKS:
                state.LINKS[uuid]["used_bytes"] += size
        reader, writer = await asyncio.open_connection(addr, port)
        if payload:
            writer.write(payload)
            await writer.drain()
        async def to_tcp():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    if not await check_quota(uuid, len(data)):
                        await websocket.close(1008)
                        break
                    state.stats["total_bytes"] += len(data)
                    writer.write(data)
                    await writer.drain()
            except:
                pass
        async def to_ws():
            try:
                first = True
                while True:
                    data = await reader.read(RELAY_BUF)
                    if not data:
                        break
                    if not await check_quota(uuid, len(data)):
                        await websocket.close(1008)
                        break
                    state.stats["total_bytes"] += len(data)
                    if first:
                        await websocket.send_bytes(b"\x00\x00" + data)
                        first = False
                    else:
                        await websocket.send_bytes(data)
            except:
                pass
        await asyncio.gather(to_tcp(), to_ws())
    except:
        pass
    finally:
        if writer:
            writer.close()
        state.connections.pop(conn_id, None)
