import os
import hashlib
import secrets

PORT = int(os.environ.get("PORT", 8000))
SECRET = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))
HOST = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")

SESSION_COOKIE = "rvg_session"
SESSION_TTL = 60 * 60 * 12

def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}{SECRET}".encode()).hexdigest()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")
AUTH = {"password_hash": hash_password(ADMIN_PASSWORD)}

def get_host() -> str:
    return HOST
