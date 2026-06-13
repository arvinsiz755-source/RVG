import logging

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


import state
from routes import client_routes
from config import CONFIG, SESSION_COOKIE
from routes import auth_routes, links_routes, stats_routes
from proxy import vless, http_proxy
from auth import is_valid_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RVG-Gateway")

app = FastAPI(title="RVG Gateway – codebox", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ───────── Middleware برای محافظت از همه مسیرها ─────────
class AuthMiddleware(BaseHTTPMiddleware):
    """
    این middleware تمام درخواست‌ها را بررسی می‌کند.
    اگر کاربر لاگین نکرده باشد، به /login هدایت می‌شود.
    مسیرهای عمومی (مثل /login، /api/login، /health) از این قانون مستثنی هستند.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # لیست مسیرهای عمومی که نیاز به لاگین ندارند
        public_paths = [
            "/login",
            "/api/login",
            "/api/me",
            "/health",
            "/",
        ]
        
        # اگر مسیر عمومی است، بدون بررسی ادامه بده
        if path in public_paths or path.startswith("/static") or path.startswith("/public"):
            return await call_next(request)
        
        # بررسی احراز هویت
        token = request.cookies.get(SESSION_COOKIE)
        if not await is_valid_session(token):
            logger.warning(f"Unauthorized access to {path} - redirecting to login")
            return RedirectResponse(url="/login", status_code=302)
        
        # ادامه درخواست
        return await call_next(request)


# اضافه کردن middleware به برنامه
app.add_middleware(AuthMiddleware)


# ───────── Routers ─────────
app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)
app.include_router(client_routes.router)


@app.on_event("startup")
async def startup():
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
    timeout = httpx.Timeout(30.0, connect=10.0)
    state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
    logger.info(f"🚀 RVG Gateway started on port {CONFIG['port']}")
    logger.info(f"🔒 Auth middleware enabled - all pages require login")


@app.on_event("shutdown")
async def shutdown():
    if state.http_client:
        await state.http_client.aclose()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=CONFIG["port"],
        log_level="info",
        workers=1,
    )
