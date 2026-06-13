import logging

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import state
from config import CONFIG
from routes import auth_routes, links_routes, stats_routes
from proxy import vless, http_proxy

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

# ───────── Routers ─────────
app.include_router(stats_routes.router)
app.include_router(auth_routes.router)
app.include_router(links_routes.router)
app.include_router(vless.router)
app.include_router(http_proxy.router)


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
