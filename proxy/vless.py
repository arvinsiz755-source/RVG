import asyncio
import secrets
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import state

router = APIRouter()

# افزایش بافر به حداکثر ممکن
RELAY_BUF = 256 * 1024  # 256KB - افزایش برای سرعت بیشتر

# تنظیمات بهینه برای TCP
TCP_NODELAY = True  # غیرفعال کردن Nagle's algorithm
TCP_KEEPIDLE = 30
TCP_KEEPINTVL = 10
TCP_KEEPCNT = 3


async def ensure_default_link():
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
                "expiry_days": 0,
            }


# کش سهمیه برای کاهش قفل‌ها
_quota_cache = {}
_quota_cache_time = {}


async def check_quota_fast(uid: str, extra_bytes: int) -> bool:
    """نسخه بسیار سریع بررسی سهمیه با کش 0.1 ثانیه"""
    import time
    
    # کش سریع (0.1 ثانیه)
    now = time.time()
    if uid in _quota_cache_time and (now - _quota_cache_time[uid]) < 0.1:
        return _quota_cache.get(uid, True)
    
    async with state.LINKS_LOCK:
        link = state.LINKS.get(uid)
        if link is None or not link["active"]:
            result = False
        elif link["limit_bytes"] == 0:
            result = True
        else:
            result = (link["used_bytes"] + extra_bytes) <= link["limit_bytes"]
    
    _quota_cache[uid] = result
    _quota_cache_time[uid] = now
    return result


async def add_usage_fast(uid: str, n: int):
    """نسخه سریع ثبت مصرف بدون قفل اضافی"""
    async with state.LINKS_LOCK:
        if uid in state.LINKS:
            state.LINKS[uid]["used_bytes"] += n


async def parse_vless_header(first_chunk: bytes):
    """نسخه بهینه شده parse header"""
    if len(first_chunk) < 24:
        raise ValueError("chunk too small")
    
    # استفاده از حافظه محلی برای سرعت بیشتر
    pos = 1  # skip version
    req_uuid = first_chunk[pos:pos+16]
    pos += 16
    
    addon_len = first_chunk[pos]
    pos += 1 + addon_len
    
    pos += 1  # skip command
    port = int.from_bytes(first_chunk[pos:pos+2], "big")
    pos += 2
    
    addr_type = first_chunk[pos]
    pos += 1
    
    if addr_type == 1:
        # IPv4
        addr_bytes = first_chunk[pos:pos+4]
        address = f"{addr_bytes[0]}.{addr_bytes[1]}.{addr_bytes[2]}.{addr_bytes[3]}"
        pos += 4
    elif addr_type == 2:
        # Domain
        domain_len = first_chunk[pos]
        pos += 1
        address = first_chunk[pos:pos+domain_len].decode("utf-8", errors="ignore")
        pos += domain_len
    elif addr_type == 3:
        # IPv6
        addr_bytes = first_chunk[pos:pos+16]
        parts = []
        for i in range(0, 16, 2):
            parts.append(f"{addr_bytes[i]:02x}{addr_bytes[i+1]:02x}")
        address = ":".join(parts)
        pos += 16
    else:
        raise ValueError(f"unknown address type: {addr_type}")
    
    payload = first_chunk[pos:]
    return req_uuid, address, port, payload


async def ws_to_tcp(websocket: WebSocket, writer: asyncio.StreamWriter, conn_id: str, link_uid: str):
    """بهینه شده برای سرعت بالا"""
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
            
            # بررسی سریع سهمیه
            if not await check_quota_fast(link_uid, size):
                await websocket.close(code=1008, reason="quota exceeded")
                break
            
            # آپدیت آمار (بدون await اضافی)
            state.stats["total_bytes"] += size
            state.stats["total_requests"] += 1
            state.connections[conn_id]["bytes"] += size
            state.hourly_traffic[datetime.now().strftime("%H:00")] += size
            
            # ثبت مصرف (غیرهمزمان ولی سریع)
            await add_usage_fast(link_uid, size)
            
            # ارسال داده با write بلافاصله
            writer.write(data)
            await writer.drain()
            
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except:
            pass


async def tcp_to_ws(websocket: WebSocket, reader: asyncio.StreamReader, conn_id: str, link_uid: str):
    """بهینه شده برای سرعت بالا - بدون تأخیر اضافی"""
    first = True
    try:
        while True:
            # خواندن با بافر بزرگتر
            data = await reader.read(RELAY_BUF)
            if not data:
                break
            
            size = len(data)
            
            if not await check_quota_fast(link_uid, size):
                await websocket.close(code=1008, reason="quota exceeded")
                break
            
            state.stats["total_bytes"] += size
            state.connections[conn_id]["bytes"] += size
            state.hourly_traffic[datetime.now().strftime("%H:00")] += size
            await add_usage_fast(link_uid, size)
            
            # ارسال مستقیم بدون کپی اضافی
            if first:
                await websocket.send_bytes(b"\x00\x00" + data)
                first = False
            else:
                await websocket.send_bytes(data)
                
    except Exception:
        pass


def optimize_socket(writer: asyncio.StreamWriter):
    """بهینه‌سازی سوکت TCP برای سرعت بالا"""
    try:
        transport = writer.transport
        if transport is not None:
            sock = transport.get_extra_info('socket')
            if sock is not None:
                # غیرفعال کردن Nagle's algorithm برای کاهش تأخیر
                sock.setsockopt(6, 1, 1)  # TCP_NODELAY
                # تنظیم Keepalive
                sock.setsockopt(6, 4, 1)  # TCP_KEEPIDLE
    except:
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
        if not await check_quota_fast(uuid, 0):
            await websocket.close(code=1008, reason="quota exceeded")
            return

        # دریافت هدر VLESS با تایم‌اوت کمتر
        first_msg = await asyncio.wait_for(websocket.receive(), timeout=10.0)
        if first_msg["type"] == "websocket.disconnect":
            return

        first_chunk = first_msg.get("bytes")
        if first_chunk is None and first_msg.get("text") is not None:
            first_chunk = first_msg["text"].encode()
        if not first_chunk:
            return

        req_uuid_raw, address, port, initial_payload = await parse_vless_header(first_chunk)

        # آپدیت آمار
        size = len(first_chunk)
        state.stats["total_bytes"] += size
        state.stats["total_requests"] += 1
        state.connections[conn_id]["bytes"] += size
        state.hourly_traffic[datetime.now().strftime("%H:00")] += size
        await add_usage_fast(uuid, size)

        # اتصال TCP با تایم‌اوت کمتر و بهینه‌سازی
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port), timeout=5.0
        )
        
        # بهینه‌سازی سوکت
        optimize_socket(writer)

        if initial_payload:
            writer.write(initial_payload)
            await writer.drain()

        # اجرای همزمان دو task
        task_up = asyncio.create_task(ws_to_tcp(websocket, writer, conn_id, uuid))
        task_down = asyncio.create_task(tcp_to_ws(websocket, reader, conn_id, uuid))

        done, pending = await asyncio.wait(
            {task_up, task_down}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()

    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        pass
    except Exception as exc:
        state.stats["total_errors"] += 1
        if len(state.error_logs) < 50:
            state.error_logs.append({"error": str(exc)[:200], "time": datetime.now().isoformat()})
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
        state.connections.pop(conn_id, None)
