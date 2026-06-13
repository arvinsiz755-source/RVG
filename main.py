# main.py - اضافه کردن تنظیم خودکار در ابتدای فایل
import os
import sys

# تنظیم خودکار متغیرهای محیطی اگر در Railway نیستند
def auto_set_env_vars():
    """تنظیم خودکار متغیرهای محیطی برای سرعت بالا"""
    
    env_defaults = {
        "UVICORN_WORKERS": "2",
        "UVICORN_LIMIT_CONCURRENCY": "2000",
        "PYTHONOPTIMIZE": "2",
        "UVICORN_BACKLOG": "4096",
        "UVICORN_LOG_LEVEL": "warning",
    }
    
    for key, default_value in env_defaults.items():
        if not os.environ.get(key):
            os.environ[key] = default_value
            print(f"✅ Auto-set {key}={default_value}")
        else:
            print(f"✓ {key}={os.environ[key]} (already set)")

# اجرای تنظیم خودکار در استارت
auto_set_env_vars()

# بقیه کدهای main.py
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

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("RVG-Gateway")

app = FastAPI(title="RVG Gateway – codebox", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public_paths = ["/login", "/api/login", "/api/me", "/health", "/"]
        
        if path in public_paths or path.startswith("/static"):
            return await call_next(request)
        
        token = request.cookies.get(SESSION_COOKIE)
        if not await is_valid_session(token):
            return RedirectResponse(url="/login", status_code=302)
        
        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)


@app.on_event("startup")
async def startup():
    limits = httpx.Limits(max_connections=2000, max_keepalive_connections=500)
    timeout = httpx.Timeout(30.0, connect=5.0)
    state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True, http2=True)
    logger.info(f"🚀 RVG Gateway started on port {CONFIG['port']}")
    
    # نمایش متغیرهای فعال
    print("\n📊 Environment variables:")
    print(f"   UVICORN_WORKERS: {os.environ.get('UVICORN_WORKERS', '2')}")
    print(f"   UVICORN_LIMIT_CONCURRENCY: {os.environ.get('UVICORN_LIMIT_CONCURRENCY', '2000')}")
    print(f"   PYTHONOPTIMIZE: {os.environ.get('PYTHONOPTIMIZE', '2')}")


@app.on_event("shutdown")
async def shutdown():
    if state.http_client:
        await state.http_client.aclose()


if __name__ == "__main__":
    workers = int(os.environ.get("UVICORN_WORKERS", 2))
    limit_concurrency = int(os.environ.get("UVICORN_LIMIT_CONCURRENCY", 2000))
    backlog = int(os.environ.get("UVICORN_BACKLOG", 4096))
    log_level = os.environ.get("UVICORN_LOG_LEVEL", "warning")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=CONFIG["port"],
        log_level=log_level,
        workers=workers,
        loop="uvloop",
        limit_concurrency=limit_concurrency,
        backlog=backlog,
    )
