import uuid
import time
from config import get_host

def generate_uuid(seed: str = None) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed)) if seed else str(uuid.uuid4())

def generate_vless_link(uuid_str: str, host: str, remark: str = "RVG") -> str:
    return f"vless://{uuid_str}@{host}:443?encryption=none&security=tls&sni={host}&fp=chrome&type=ws&path=/ws/{uuid_str}#{remark}"

def parse_size_to_bytes(value: float, unit: str) -> int:
    unit = unit.upper()
    mult = {"B": 1, "KB": 1024, "MB": 1048576, "GB": 1073741824}
    return int(value * mult.get(unit, 1048576))

def uptime(start_time: float = None) -> str:
    import state
    secs = int(time.time() - (start_time or state.stats["start_time"]))
    return f"{secs//3600:02d}:{(secs%3600)//60:02d}:{secs%60:02d}"
