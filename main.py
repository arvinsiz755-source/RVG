import logging
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

import state
from config import CONFIG, SESSION_COOKIE
from routes import auth_routes, links_routes, stats_routes
from proxy import vless, http_proxy
from auth import is_valid_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RVG-Gateway")

app = FastAPI(title="RVG Gateway – codebox", docs_url=None, redoc_url=None)

# اضافه کردن middlewareهای بهینه‌سازی
app.add_middleware(GZipMiddleware, minimum_size=500)  # فشرده‌سازی پاسخ‌ها
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware برای کش کردن پاسخ‌های استاتیک
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/static", "/public")):
            response.headers["Cache-Control"] = "public, max-age=3600"
        elif request.url.path in ["/stats", "/api/links", "/api/clients/"]:
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.add_middleware(CacheControlMiddleware)


# Middleware برای محافظت از مسیرها
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public_paths = ["/login", "/api/login", "/api/me", "/health", "/", "/api/railway/setup-domain"]
        
        if path in public_paths or path.startswith("/static") or path.startswith("/public"):
            return await call_next(request)
        
        token = request.cookies.get(SESSION_COOKIE)
        if not await is_valid_session(token):
            return RedirectResponse(url="/login", status_code=302)
        
        return await call_next(request)


app.add_middleware(AuthMiddleware)

# ───────── Routers ─────────
app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)

# اضافه کردن client_routes اگر وجود دارد
try:
    from routes import client_routes
    app.include_router(client_routes.router)
except ImportError:
    pass


@app.on_event("startup")
async def startup():
    # بهینه‌سازی connection pool
    limits = httpx.Limits(
        max_connections=1000,  # افزایش حداکثر اتصالات
        max_keepalive_connections=200,  # افزایش نگهداری اتصالات
        keepalive_expiry=30.0  # کاهش زمان نگهداری برای آزادسازی سریعتر
    )
    timeout = httpx.Timeout(30.0, connect=5.0)  # کاهش timeout اتصال
    state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True, http2=True)  # فعال کردن HTTP/2
    logger.info(f"🚀 RVG Gateway started on port {CONFIG['port']} with optimized settings")

@app.on_event("startup")
async def startup():
    # تنظیم خودکار متغیرهای محیطی
    try:
        from railway_setup import setup_railway_env
        await setup_railway_env()
    except ImportError:
        pass

@app.on_event("shutdown")
async def shutdown():
    if state.http_client:
        await state.http_client.aclose()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=CONFIG["port"],
        log_level="warning",  # کاهش لاگ برای سرعت بیشتر
        workers=4,  # افزایش workerها
        limit_concurrency=1000,  # محدودیت همزمانی
        backlog=2048,  # افزایش بکلاگ
        loop="uvloop",  # استفاده از uvloop (فقط روی لینوکس)
    )
