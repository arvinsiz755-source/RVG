from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import state
from auth import create_session, is_valid_session, destroy_session, require_auth, set_session_cookie, clear_session_cookie
from config import AUTH, SESSION_COOKIE, hash_password
from proxy.vless import ensure_default_link

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


# ───────── API ─────────
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
    clear_session_cookie(resp)
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

    # همه‌ی سشن‌های دیگر باطل می‌شوند، فقط سشن فعلی باقی می‌ماند
    current_token = request.cookies.get(SESSION_COOKIE)
    async with state.SESSIONS_LOCK:
        state.SESSIONS.clear()
        if current_token:
            state.SESSIONS[current_token] = __import__("time").time() + 43200

    return {"ok": True}


# ───────── Pages با محافظت ─────────
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if await is_valid_session(token):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=_read_template("login.html"))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # بررسی احراز هویت قبل از نمایش صفحه
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        return RedirectResponse(url="/login")
    await ensure_default_link()
    return HTMLResponse(content=_read_template("dashboard.html"))


@router.get("/")
async def root_redirect(request: Request):
    """ری‌دایرکت روت به دشبورد یا لاگین"""
    token = request.cookies.get(SESSION_COOKIE)
    if await is_valid_session(token):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")
