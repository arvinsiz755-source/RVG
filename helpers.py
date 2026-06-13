import uuid
import re
import time
from config import get_host as config_get_host

def generate_uuid(seed: str = None) -> str:
    if seed:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))
    return str(uuid.uuid4())

def generate_vless_link(uuid_str: str, host: str, remark: str = "RVG") -> str:
    path = f"/ws/{uuid_str}"
    params = f"encryption=none&security=tls&sni={host}&fp=chrome&type=ws&path={path}"
    return f"vless://{uuid_str}@{host}:443?{params}#{remark}"

def get_host() -> str:
    return config_get_host()

def parse_size_to_bytes(value: float, unit: str) -> int:
    unit = unit.upper().strip()
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
    }
    return int(value * multipliers.get(unit, 1024 * 1024))

def format_bytes(bytes_count: int) -> str:
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"

def extract_uuid_from_vless(vless_link: str) -> str | None:
    match = re.search(r'vless://([a-f0-9\-]+)@', vless_link)
    return match.group(1) if match else None

def uptime(start_time: float = None) -> str:
    import state
    start = start_time if start_time is not None else state.stats.get("start_time", time.time())
    secs = int(time.time() - start)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
