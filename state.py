# state.py - نسخه بهینه‌سازی شده با کش داخلی
import asyncio
import time
from collections import deque, defaultdict
from functools import lru_cache
import httpx

# ───────── Connections / Stats ─────────
connections: dict = {}
stats = {
    "total_bytes": 0,
    "total_requests": 0,
    "total_errors": 0,
    "start_time": time.time(),
}
error_logs: deque = deque(maxlen=50)
hourly_traffic: dict = defaultdict(int)

# ───────── HTTP client ─────────
http_client: httpx.AsyncClient | None = None

# ───────── Links ─────────
LINKS: dict = {}
LINKS_LOCK = asyncio.Lock()

# ───────── Sessions ─────────
SESSIONS: dict = {}
SESSIONS_LOCK = asyncio.Lock()

# ───────── Cache برای کاهش بار ─────────
_cache = {}
_cache_lock = asyncio.Lock()


async def get_cached(key: str, ttl: int = 5) -> any:
    """دریافت از کش با TTL پیش‌فرض 5 ثانیه"""
    async with _cache_lock:
        if key in _cache:
            value, expiry = _cache[key]
            if time.time() < expiry:
                return value
            del _cache[key]
    return None


async def set_cached(key: str, value: any, ttl: int = 5):
    """ذخیره در کش"""
    async with _cache_lock:
        _cache[key] = (value, time.time() + ttl)


async def clear_cache():
    """پاک کردن کل کش"""
    async with _cache_lock:
        _cache.clear()


def uptime() -> str:
    secs = int(time.time() - stats["start_time"])
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
