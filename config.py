import os
import hashlib
import secrets

CONFIG = {
    "port": int(os.environ.get("PORT", 8000)),
    "secret": os.environ.get("SECRET_KEY", secrets.token_urlsafe(32)),
    "host": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost"),
}

# ───────── Auth config ─────────
SESSION_COOKIE = "rvg_session"
# مدت اعتبار سشن روی سرور (محافظتی - حتی اگر کوکی session-only پاک نشود)
SESSION_TTL = 60 * 60 * 12  # 12 ساعت


def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}{CONFIG['secret']}".encode()).hexdigest()


AUTH = {
    "password_hash": hash_password(os.environ.get("ADMIN_PASSWORD", "123456")),
}


def get_host() -> str:
    return os.environ.get("RAILWAY_PUBLIC_DOMAIN", CONFIG["host"])
