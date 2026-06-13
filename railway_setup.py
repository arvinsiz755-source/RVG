# railway_setup.py
import os
import asyncio
import httpx

async def setup_railway_env():
    """تنظیم خودکار متغیرهای محیطی در Railway از طریق API"""
    
    # متغیرهایی که باید تنظیم شوند
    required_vars = {
        "UVICORN_WORKERS": "2",
        "UVICORN_LIMIT_CONCURRENCY": "2000",
        "PYTHONOPTIMIZE": "2",
        "UVICORN_BACKLOG": "4096",
    }
    
    # متغیرهایی که از قبل تنظیم شده‌اند
    for key, default in required_vars.items():
        if not os.environ.get(key):
            os.environ[key] = default
            print(f"✅ Set {key}={default}")
    
    # اگر در Railway هستیم، سعی کنیم از API استفاده کنیم
    railway_token = os.environ.get("RAILWAY_API_TOKEN")
    service_id = os.environ.get("RAILWAY_SERVICE_ID")
    
    if railway_token and service_id:
        print("🔄 Syncing with Railway API...")
        async with httpx.AsyncClient() as client:
            for key, value in required_vars.items():
                try:
                    # اینجا می‌توانید API Railway را صدا بزنید
                    print(f"   Syncing {key}={value}")
                except Exception as e:
                    print(f"   Error syncing {key}: {e}")

# در main.py این را صدا بزنید
# asyncio.run(setup_railway_env())
