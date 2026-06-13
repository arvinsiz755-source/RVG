from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from auth import require_auth, is_valid_session, create_session, set_session_cookie
from config import SESSION_COOKIE

router = APIRouter()
TEMPLATES = Path(__file__).parent.parent / "templates"

def read_template(name: str) -> str:
    try:
        return (TEMPLATES / name).read_text(encoding="utf-8")
    except:
        return "<h1>Template not found</h1>"

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse(content=read_template("login.html"))

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/login")
    return HTMLResponse(content=read_template("dashboard.html"))

@router.get("/")
async def root(request: Request):
    if await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")
