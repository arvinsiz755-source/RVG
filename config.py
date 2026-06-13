import hashlib
import secrets

PORT = 8000
SECRET = "my-super-secret-key-change-this-in-production"
HOST = "localhost"

SESSION_COOKIE = "rvg_session"
SESSION_TTL = 60 * 60 * 12

def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}{SECRET}".encode()).hexdigest()

# رمز پیش‌فرض: 123456
ADMIN_PASSWORD = "123456"
AUTH = {"password_hash": hash_password(ADMIN_PASSWORD)}

def get_host() -> str:
    return HOST
