import logging
import time
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

import state
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


# Middleware برای محافظت
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        public_paths = [
            "/login", "/api/login", "/api/me", "/health", "/", 
            "/health/simple", "/favicon.ico"
        ]
        
        if path in public_paths or path.startswith("/static") or path.startswith("/public"):
            return await call_next(request)
        
        token = request.cookies.get(SESSION_COOKIE)
        if not await is_valid_session(token):
            return RedirectResponse(url="/login", status_code=302)
        
        return await call_next(request)


app.add_middleware(AuthMiddleware)


# Healthcheck سریع
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/health/simple")
async def health_simple():
    return {"ok": True}


# ───────── Routers ─────────
app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)

# Client routes (اختیاری - اگر فایل وجود داشت اضافه کن)
try:
    from routes import client_routes
    app.include_router(client_routes.router)
    logger.info("✅ Client routes loaded")
except ImportError:
    logger.info("⚠️ Client routes not available")


@app.on_event("startup")
async def startup():
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
    timeout = httpx.Timeout(30.0, connect=10.0)
    state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
    logger.info(f"🚀 RVG Gateway started on port {CONFIG['port']}")


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
