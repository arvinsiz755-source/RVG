import logging
import time
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

import state
from config import CONFIG, SESSION_COOKIE
from routes import auth_routes, links_routes, stats_routes
from proxy import vless, http_proxy
from auth import is_valid_session

logging.basicConfig(level=logging.WARNING)  # کاهش لاگ برای سرعت
logger = logging.getLogger("RVG-Gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    limits = httpx.Limits(
        max_connections=2000,  # افزایش
        max_keepalive_connections=500,
        keepalive_expiry=30
    )
    timeout = httpx.Timeout(30.0, connect=5.0)
    state.http_client = httpx.AsyncClient(
        limits=limits, 
        timeout=timeout, 
        follow_redirects=True,
        http2=True  # فعال کردن HTTP/2
    )
    logger.info(f"🚀 RVG Gateway started on port {CONFIG['port']}")
    
    yield
    
    # Shutdown
    if state.http_client:
        await state.http_client.aclose()


app = FastAPI(
    title="RVG Gateway – codebox", 
    docs_url=None, 
    redoc_url=None,
    lifespan=lifespan
)

# فشرده‌سازی پاسخ‌ها
app.add_middleware(GZipMiddleware, minimum_size=500)

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


# ───────── Routers ─────────
app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=CONFIG["port"],
        log_level="warning",
        workers=2,  # کاهش workerها برای جلوگیری از race condition
        loop="uvloop",
        limit_concurrency=2000,
        backlog=4096,
        timeout_keep_alive=30,
    )
