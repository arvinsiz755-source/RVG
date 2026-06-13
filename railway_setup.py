# railway_setup.py
import os
import json
import httpx
from typing import Optional

async def setup_railway_env():
    """تنظیم خودکار متغیرهای محیطی در Railway"""
    
    env_vars = {
        "WEB_CONCURRENCY": "4",
        "UVICORN_WORKERS": "4",
        "PYTHONOPTIMIZE": "2",
        "UVICORN_LIMIT_CONCURRENCY": "1000",
        "UVICORN_BACKLOG": "2048",
        "UVICORN_LOG_LEVEL": "warning",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1"
    }
    
    # اگر در Railway هستیم، سعی کنیم از API Railway استفاده کنیم
    railway_api_token = os.getenv("RAILWAY_API_TOKEN")
    service_id = os.getenv("RAILWAY_SERVICE_ID")
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID")
    
    if railway_api_token and service_id and environment_id:
        print("🔄 Setting up Railway environment variables...")
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {railway_api_token}",
                "Content-Type": "application/json"
            }
            
            for key, value in env_vars.items():
                # بررسی اگر متغیر از قبل وجود ندارد
                if not os.getenv(key):
                    try:
                        mutation = """
                        mutation UpdateVariable($envId: String!, $serviceId: String!, $name: String!, $value: String!) {
                            updateServiceVariable(
                                environmentId: $envId,
                                serviceId: $serviceId,
                                name: $name,
                                value: $value
                            ) {
                                id
                                name
                                value
                            }
                        }
                        """
                        
                        variables = {
                            "envId": environment_id,
                            "serviceId": service_id,
                            "name": key,
                            "value": value
                        }
                        
                        response = await client.post(
                            "https://backboard.railway.app/graphql/v2",
                            json={"query": mutation, "variables": variables},
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            print(f"✅ Added {key}={value}")
                        else:
                            print(f"⚠️ Could not add {key}")
                            
                    except Exception as e:
                        print(f"❌ Error setting {key}: {e}")
        
        print("✅ Railway environment setup complete!")
    
    # تنظیم متغیرهای محیطی در زمان اجرا
    for key, value in env_vars.items():
        if not os.getenv(key):
            os.environ[key] = value
            print(f"✅ Set {key}={value}")

# در main.py، در startup، این تابع را صدا بزنید
