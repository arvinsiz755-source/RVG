import secrets
import time

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

from config import SESSION_COOKIE, SESSION_TTL, AUTH, hash_password
from state import SESSIONS, SESSIONS_LOCK

router = APIRouter()


# ───────── Session helpers ─────────
async def create_session() -> str:
    token = secrets.token_urlsafe(32)
    async with SESSIONS_LOCK:
        SESSIONS[token] = time.time() + SESSION_TTL
    return token


async def is_valid_session(token: str | None) -> bool:
    if not token:
        return False
    async with SESSIONS_LOCK:
        exp = SESSIONS.get(token)
        if exp is None:
            return False
        if exp < time.time():
            SESSIONS.pop(token, None)
            return False
        return True


async def destroy_session(token: str | None):
    if not token:
        return
    async with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


async def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return token


def set_session_cookie(resp, token: str):
    """
    نکته مهم امنیتی:
    کوکی به‌صورت "session cookie" تنظیم می‌شود (بدون max_age/expires)
    یعنی با بسته‌شدن مرورگر/تب، کوکی حذف می‌شود و کاربر باید دوباره
    لاگین کند. این یعنی هر بار که صفحه به‌صورت تازه (مرورگر جدید/تب جدید
    بعد از بسته‌شدن کامل مرورگر) باز شود، لاگین مجدد لازم است.
    در سمت سرور هم SESSION_TTL به‌عنوان یک محافظت اضافه (۱۲ ساعت) وجود دارد.
    """
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        # max_age عمداً ست نمی‌شود => کوکی session-only
        httponly=True,
        samesite="lax",
        path="/",
        secure=True,
    )


# ───────── Endpoints ─────────
@router.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    password = str(body.get("password") or "")
    if hash_password(password) != AUTH["password_hash"]:
        raise HTTPException(status_code=401, detail="رمز عبور اشتباه است")

    token = await create_session()
    resp = JSONResponse({"ok": True})
    set_session_cookie(resp, token)
    return resp


@router.post("/api/logout")
async def api_logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    await destroy_session(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@router.get("/api/me")
async def api_me(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    valid = await is_valid_session(token)
    return {"authenticated": valid}


@router.post("/api/change-password")
async def api_change_password(request: Request, _=Depends(require_auth)):
    body = await request.json()
    current = str(body.get("current_password") or "")
    new = str(body.get("new_password") or "")

    if hash_password(current) != AUTH["password_hash"]:
        raise HTTPException(status_code=400, detail="رمز فعلی اشتباه است")
    if len(new) < 4:
        raise HTTPException(status_code=400, detail="رمز جدید باید حداقل ۴ کاراکتر باشد")

    AUTH["password_hash"] = hash_password(new)

    # همه سشن‌های دیگر را باطل می‌کنیم، فقط سشن فعلی باقی می‌ماند
    current_token = request.cookies.get(SESSION_COOKIE)
    async with SESSIONS_LOCK:
        SESSIONS.clear()
        if current_token:
            SESSIONS[current_token] = time.time() + SESSION_TTL

    return {"ok": True}


# ───────── Login page ─────────
def register_login_page(app, login_html: str):
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        token = request.cookies.get(SESSION_COOKIE)
        if await is_valid_session(token):
            return RedirectResponse(url="/dashboard")
        return HTMLResponse(content=login_html)
