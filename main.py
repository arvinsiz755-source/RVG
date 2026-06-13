import os
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# تنظیم پورت مهم - Railway از 8080 استفاده می‌کند
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RVG")

@asynccontextmanager
async def lifespan(app: FastAPI):
    import state
    import httpx
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
    state.http_client = httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(30.0))
    logger.info(f"🚀 RVG Gateway started on port {PORT}")
    yield
    if state.http_client:
        await state.http_client.aclose()

app = FastAPI(title="RVG Gateway", docs_url=None, redoc_url=None, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from config import SESSION_COOKIE
        from auth import is_valid_session
        path = request.url.path
        # مسیرهای عمومی - مهم: health باید بدون احراز هویت باشد
        public_paths = ["/login", "/api/login", "/api/me", "/health", "/", "/favicon.ico", "/health/simple"]
        if path in public_paths or path.startswith("/static") or path.startswith("/register"):
            return await call_next(request)
        token = request.cookies.get(SESSION_COOKIE)
        if not await is_valid_session(token):
            return RedirectResponse(url="/login", status_code=302)
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# Healthcheck سریع - باید خیلی سریع جواب بده
@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}

@app.get("/health/simple")
async def health_simple():
    return "ok"

# Import routers
from routes import auth_routes, links_routes, stats_routes
from proxy import vless, http_proxy

app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)

# ثبت‌نام خودکار (اگر فایل وجود دارد)
try:
    from routes import register_routes
    app.include_router(register_routes.router)
    logger.info("✅ Register routes loaded")
except ImportError:
    logger.info("⚠️ Register routes not available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, workers=2)
