# proxy/vless.py - بهینه‌سازی شده
import asyncio
import secrets
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import state

router = APIRouter()

# افزایش بافر برای سرعت بیشتر
RELAY_BUF = 128 * 1024  # 128KB به جای 64KB

# کش برای بررسی سهمیه
_quota_cache = {}
_quota_cache_lock = asyncio.Lock()


async def check_quota_cached(uid: str, extra_bytes: int) -> bool:
    """نسخه کش شده بررسی سهمیه"""
    cache_key = f"quota_{uid}"
    
    async with _quota_cache_lock:
        if cache_key in _quota_cache:
            cached_result, cached_time = _quota_cache[cache_key]
            # کش به مدت 0.5 ثانیه معتبر است
            if datetime.now().timestamp() - cached_time < 0.5:
                return cached_result
    
    async with state.LINKS_LOCK:
        link = state.LINKS.get(uid)
        if link is None:
            result = False
        elif not link["active"]:
            result = False
        elif link["limit_bytes"] == 0:
            result = True
        else:
            result = (link["used_bytes"] + extra_bytes) <= link["limit_bytes"]
    
    async with _quota_cache_lock:
        _quota_cache[cache_key] = (result, datetime.now().timestamp())
    
    return result


async def ensure_default_link():
    """اگر هیچ لینکی وجود نداره، یک لینک پیش‌فرض بی‌نهایت می‌سازه."""
    from helpers import generate_uuid
    async with state.LINKS_LOCK:
        if not state.LINKS:
            uid = generate_uuid("default")
            state.LINKS[uid] = {
                "label": "لینک پیش‌فرض",
                "limit_bytes": 0,
                "used_bytes": 0,
                "created_at": datetime.now().isoformat(),
                "active": True,
            }


async def parse_vless_header(first_chunk: bytes):
    if len(first_chunk) < 24:
        raise ValueError("chunk too small")
    # بهینه‌سازی: حذف متغیرهای اضافی
    pos = 0
    pos += 1  # version
    req_uuid = first_chunk[pos:pos + 16]
    pos += 16
    addon_len = first_chunk[pos]
    pos += 1 + addon_len
    pos += 1  # command
    port = int.from_bytes(first_chunk[pos:pos + 2], "big")
    pos += 2
    addr_type = first_chunk[pos]
    pos += 1

    if addr_type == 1:
        address = ".".join(str(b) for b in first_chunk[pos:pos + 4])
        pos += 4
    elif addr_type == 2:
        domain_len = first_chunk[pos]
        pos += 1
        address = first_chunk[pos:pos + domain_len].decode("utf-8", errors="ignore")
        pos += domain_len
    elif addr_type == 3:
        addr_bytes = first_chunk[pos:pos + 16]
        pos += 16
        address = ":".join(f"{addr_bytes[i]:02x}{addr_bytes[i+1]:02x}" for i in range(0, 16, 2))
    else:
        raise ValueError(f"unknown address type: {addr_type}")

    payload = first_chunk[pos:]
    return req_uuid, address, port, payload


async def ws_to_tcp(websocket: WebSocket, writer: asyncio.StreamWriter, conn_id: str, link_uid: str):
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data is None and msg.get("text") is not None:
                data = msg["text"].encode()
            if not data:
                continue

            size = len(data)
            if not await check_quota_cached(link_uid, size):
                await websocket.close(code=1008, reason="quota exceeded")
                break

            state.stats["total_bytes"] += size
            state.stats["total_requests"] += 1
            if conn_id in state.connections:
                state.connections[conn_id]["bytes"] += size
            state.hourly_traffic[datetime.now().strftime("%H:00")] += size
            
            async with state.LINKS_LOCK:
                if link_uid in state.LINKS:
                    state.LINKS[link_uid]["used_bytes"] += size

            writer.write(data)
            await writer.drain()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            writer.write_eof()
        except Exception:
            pass


async def tcp_to_ws(websocket: WebSocket, reader: asyncio.StreamReader, conn_id: str, link_uid: str):
    first = True
    try:
        while True:
            data = await reader.read(RELAY_BUF)
            if not data:
                break

            size = len(data)
            if not await check_quota_cached(link_uid, size):
                await websocket.close(code=1008, reason="quota exceeded")
                break

            state.stats["total_bytes"] += size
            if conn_id in state.connections:
                state.connections[conn_id]["bytes"] += size
            state.hourly_traffic[datetime.now().strftime("%H:00")] += size
            
            async with state.LINKS_LOCK:
                if link_uid in state.LINKS:
                    state.LINKS[link_uid]["used_bytes"] += size

            if first:
                await websocket.send_bytes(b"\x00\x00" + data)
                first = False
            else:
                await websocket.send_bytes(data)
    except Exception:
        pass


@router.websocket("/ws/{uuid}")
async def websocket_tunnel(websocket: WebSocket, uuid: str):
    await ensure_default_link()
    await websocket.accept()
    conn_id = secrets.token_urlsafe(8)
    state.connections[conn_id] = {
        "uuid": uuid,
        "connected_at": datetime.now().isoformat(),
        "bytes": 0,
    }

    writer = None
    try:
        if not await check_quota_cached(uuid, 0):
            await websocket.close(code=1008, reason="quota exceeded")
            return

        first_msg = await asyncio.wait_for(websocket.receive(), timeout=15.0)
        if first_msg["type"] == "websocket.disconnect":
            return

        first_chunk = first_msg.get("bytes")
        if first_chunk is None and first_msg.get("text") is not None:
            first_chunk = first_msg["text"].encode()
        if not first_chunk:
            return

        req_uuid_raw, address, port, initial_payload = await parse_vless_header(first_chunk)

        size = len(first_chunk)
        state.stats["total_bytes"] += size
        state.stats["total_requests"] += 1
        if conn_id in state.connections:
            state.connections[conn_id]["bytes"] += size
        state.hourly_traffic[datetime.now().strftime("%H:00")] += size
        
        async with state.LINKS_LOCK:
            if uuid in state.LINKS:
                state.LINKS[uuid]["used_bytes"] += size

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port), timeout=10.0
        )

        if initial_payload:
            writer.write(initial_payload)
            await writer.drain()

        task_up = asyncio.create_task(ws_to_tcp(websocket, writer, conn_id, uuid))
        task_down = asyncio.create_task(tcp_to_ws(websocket, reader, conn_id, uuid))

        done, pending = await asyncio.wait(
            {task_up, task_down}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        state.stats["total_errors"] += 1
        state.error_logs.append({"error": str(exc), "time": datetime.now().isoformat()})
    finally:
        if writer:
            try:
                writer.close()
            except Exception:
                pass
        state.connections.pop(conn_id, None)
