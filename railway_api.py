"""
این ماژول با Railway Public API (GraphQL) صحبت می‌کند تا:
  1) برای سرویس یک دامین عمومی رندوم بسازد (serviceDomainCreate)
  2) سرویس را ری‌دیپلوی کند تا دامین جدید فعال شود (serviceInstanceRedeploy)

برای کار کردن این بخش باید متغیرهای محیطی زیر در Railway ست شوند:
  - RAILWAY_API_TOKEN     : یک Project Token یا Account Token از Railway
  - RAILWAY_SERVICE_ID    : شناسه سرویس (از تنظیمات سرویس در Railway)
  - RAILWAY_ENVIRONMENT_ID: شناسه environment (معمولاً production)

اگر این متغیرها ست نشده باشند، endpoint مربوطه خطای واضح برمی‌گرداند
و بقیه‌ی برنامه بدون مشکل کار می‌کند (این بخش کاملاً اختیاری است).
"""

import os
import httpx
from fastapi import APIRouter, Depends, HTTPException

from auth import require_auth

router = APIRouter()

RAILWAY_GRAPHQL_URL = "https://backboard.railway.app/graphql/v2"


def _railway_env():
    token = os.environ.get("RAILWAY_API_TOKEN")
    service_id = os.environ.get("RAILWAY_SERVICE_ID")
    environment_id = os.environ.get("RAILWAY_ENVIRONMENT_ID")
    return token, service_id, environment_id


async def _graphql(query: str, variables: dict, token: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            RAILWAY_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        data = r.json()
        if "errors" in data and data["errors"]:
            raise HTTPException(status_code=502, detail=str(data["errors"]))
        return data["data"]


async def create_service_domain(token: str, service_id: str, environment_id: str) -> str:
    query = """
    mutation($input: ServiceDomainCreateInput!) {
      serviceDomainCreate(input: $input) {
        domain
      }
    }
    """
    variables = {"input": {"serviceId": service_id, "environmentId": environment_id}}
    data = await _graphql(query, variables, token)
    return data["serviceDomainCreate"]["domain"]


async def redeploy_service(token: str, service_id: str, environment_id: str):
    query = """
    mutation($serviceId: String!, $environmentId: String!) {
      serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
    }
    """
    variables = {"serviceId": service_id, "environmentId": environment_id}
    await _graphql(query, variables, token)


@router.post("/api/railway/setup-domain")
async def setup_domain(_=Depends(require_auth)):
    """
    یک دامین عمومی جدید برای سرویس می‌سازد و سرویس را ری‌دیپلوی می‌کند
    تا دامین جدید فعال شود.
    """
    token, service_id, environment_id = _railway_env()
    if not token or not service_id or not environment_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "برای استفاده از این قابلیت باید متغیرهای محیطی "
                "RAILWAY_API_TOKEN, RAILWAY_SERVICE_ID, RAILWAY_ENVIRONMENT_ID "
                "را در سرویس Railway تنظیم کنید."
            ),
        )

    domain = await create_service_domain(token, service_id, environment_id)
    await redeploy_service(token, service_id, environment_id)

    return {
        "ok": True,
        "domain": domain,
        "message": "دامین جدید ساخته شد و سرویس در حال ری‌دیپلوی است. چند دقیقه صبر کنید.",
    }


@router.get("/api/railway/status")
async def railway_status(_=Depends(require_auth)):
    token, service_id, environment_id = _railway_env()
    return {
        "configured": bool(token and service_id and environment_id),
    }
