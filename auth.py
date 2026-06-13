import secrets
import time
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from config import SESSION_COOKIE, SESSION_TTL, AUTH, hash_password
from state import SESSIONS, SESSIONS_LOCK

router = APIRouter()

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
    if token:
        async with SESSIONS_LOCK:
            SESSIONS.pop(token, None)

async def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return token

def set_session_cookie(resp, token: str):
    resp.set_cookie(key=SESSION_COOKIE, value=token, httponly=True, samesite="lax", path="/", secure=False)

@router.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    password = str(body.get("password", ""))
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
