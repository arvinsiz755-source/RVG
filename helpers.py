import uuid
import re
from config import get_host as config_get_host


def generate_uuid(seed: str = None) -> str:
    """تولید UUID یکتا (اگر seed داده شود، UUID ثابت بر اساس seed تولید می‌کند)"""
    if seed:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))
    return str(uuid.uuid4())


def generate_vless_link(uuid: str, host: str, remark: str = "RVG") -> str:
    """
    ساخت لینک VLESS با فرمت استاندارد
    فرمت: vless://UUID@HOST:443?encryption=none&security=tls&sni=HOST&fp=chrome&type=ws&path=%2Fws%2FUUID#REMARK
    """
    # مسیر WebSocket بر اساس UUID
    path = f"/ws/{uuid}"
    
    # پارامترهای لینک
    params = (
        f"encryption=none"
        f"&security=tls"
        f"&sni={host}"
        f"&fp=chrome"
        f"&type=ws"
        f"&path={path}"
    )
    
    # ساخت لینک نهایی
    vless_link = f"vless://{uuid}@{host}:443?{params}#{remark}"
    
    return vless_link


def get_host() -> str:
    """دریافت آدرس هاست از config"""
    return config_get_host()


def parse_size_to_bytes(value: float, unit: str) -> int:
    """
    تبدیل حجم به بایت
    unit می‌تواند: B, KB, MB, GB, TB
    """
    unit = unit.upper().strip()
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
        "TB": 1024 * 1024 * 1024 * 1024,
    }
    
    if unit not in multipliers:
        raise ValueError(f"Unknown unit: {unit}")
    
    return int(value * multipliers[unit])


def format_bytes(bytes_count: int) -> str:
    """تبدیل بایت به فرمت خوانا (MB/GB/...)"""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def extract_uuid_from_vless(vless_link: str) -> str | None:
    """استخراج UUID از لینک VLESS"""
    match = re.search(r'vless://([a-f0-9\-]+)@', vless_link)
    if match:
        return match.group(1)
    return None
