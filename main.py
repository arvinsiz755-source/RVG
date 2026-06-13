import os
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("RVG")

# تنظیم خودکار متغیرهای محیطی
os.environ.setdefault("UVICORN_WORKERS", "2")
os.environ.setdefault("UVICORN_LIMIT_CONCURRENCY", "2000")

@asynccontextmanager
async def lifespan(app: FastAPI):
    import state
    import httpx
    limits = httpx.Limits(max_connections=2000, max_keepalive_connections=500)
    state.http_client = httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(30.0), http2=True)
    logger.info("🚀 RVG Gateway started")
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
        public_paths = ["/login", "/api/login", "/api/me", "/health", "/", "/favicon.ico"]
        if path in public_paths or path.startswith("/static"):
            return await call_next(request)
        token = request.cookies.get(SESSION_COOKIE)
        if not await is_valid_session(token):
            return RedirectResponse(url="/login", status_code=302)
        return await call_next(request)

app.add_middleware(AuthMiddleware)

@app.get("/health")
async def health():
    return {"status": "ok", "time": time.time()}

# Import routers
from routes import auth_routes, links_routes, stats_routes
from proxy import vless, http_proxy

app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=2, loop="uvloop")
