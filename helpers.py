# helpers.py - نسخه بهینه‌سازی شده
import uuid
import re
import time
from functools import lru_cache
from config import get_host as config_get_host


@lru_cache(maxsize=128)
def generate_uuid(seed: str = None) -> str:
    """تولید UUID با کش برای تکرار"""
    if seed:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))
    return str(uuid.uuid4())


@lru_cache(maxsize=256)
def generate_vless_link(uuid: str, host: str, remark: str = "RVG") -> str:
    """ساخت لینک VLESS با کش"""
    path = f"/ws/{uuid}"
    params = (
        f"encryption=none"
        f"&security=tls"
        f"&sni={host}"
        f"&fp=chrome"
        f"&type=ws"
        f"&path={path}"
    )
    return f"vless://{uuid}@{host}:443?{params}#{remark}"


@lru_cache(maxsize=1)
def get_host() -> str:
    """دریافت آدرس هاست با کش دائمی"""
    return config_get_host()


# کش برای تبدیل حجم به بایت
_size_cache = {}


def parse_size_to_bytes(value: float, unit: str) -> int:
    """تبدیل حجم به بایت با کش"""
    cache_key = f"{value}:{unit}"
    if cache_key in _size_cache:
        return _size_cache[cache_key]
    
    unit = unit.upper().strip()
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
        "TB": 1024 * 1024 * 1024 * 1024,
    }
    
    result = int(value * multipliers.get(unit, 1024 * 1024))
    _size_cache[cache_key] = result
    return result


def format_bytes(bytes_count: int) -> str:
    """تبدیل بایت به فرمت خوانا"""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def extract_uuid_from_vless(vless_link: str) -> str | None:
    """استخراج UUID از لینک VLESS"""
    match = re.search(r'vless://([a-f0-9\-]+)@', vless_link)
    return match.group(1) if match else None


def uptime(start_time: float = None) -> str:
    """محاسبه زمان آپتایم"""
    import state
    start = start_time if start_time is not None else state.stats["start_time"]
    secs = int(time.time() - start)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
