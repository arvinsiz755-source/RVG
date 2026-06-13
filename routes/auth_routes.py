from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import time
import secrets

import state
from config import SESSION_COOKIE, SESSION_TTL, AUTH, hash_password

router = APIRouter()

TEMPLATES = Path(__file__).parent.parent / "templates"

def read_template(name: str) -> str:
    try:
        return (TEMPLATES / name).read_text(encoding="utf-8")
    except:
        return "<h1>Template not found</h1>"

# ========== Session Helpers ==========
async def create_session() -> str:
    token = secrets.token_urlsafe(32)
    async with state.SESSIONS_LOCK:
        state.SESSIONS[token] = time.time() + SESSION_TTL
    return token

async def is_valid_session(token: str | None) -> bool:
    if not token:
        return False
    async with state.SESSIONS_LOCK:
        exp = state.SESSIONS.get(token)
        if exp is None:
            return False
        if exp < time.time():
            state.SESSIONS.pop(token, None)
            return False
        return True

async def destroy_session(token: str | None):
    if token:
        async with state.SESSIONS_LOCK:
            state.SESSIONS.pop(token, None)

async def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return token

def set_session_cookie(resp, token: str):
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )

# ========== API Routes ==========
@router.post("/api/login")
async def api_login(request: Request):
    try:
        body = await request.json()
        password = str(body.get("password") or "")
        
        if hash_password(password) != AUTH["password_hash"]:
            raise HTTPException(status_code=401, detail="رمز عبور اشتباه است")
        
        token = await create_session()
        resp = JSONResponse({"ok": True, "message": "ورود موفق"})
        set_session_cookie(resp, token)
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

    current_token = request.cookies.get(SESSION_COOKIE)
    async with state.SESSIONS_LOCK:
        state.SESSIONS.clear()
        if current_token:
            state.SESSIONS[current_token] = time.time() + SESSION_TTL

    return {"ok": True}

# ========== Page Routes ==========
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if await is_valid_session(token):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=read_template("login.html"))

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        return RedirectResponse(url="/login")
    return HTMLResponse(content=read_template("dashboard.html"))

@router.get("/")
async def root_redirect(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if await is_valid_session(token):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")
