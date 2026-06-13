# routes/client_routes.py
from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Optional

from auth import require_auth
from client_manager import client_manager
from helpers import generate_vless_link, get_host

router = APIRouter(prefix="/api/clients", tags=["Clients"])


@router.get("/")
async def get_all_clients(_=Depends(require_auth)):
    """دریافت لیست همه کاربران"""
    clients = client_manager.get_all_clients()
    host = get_host()
    
    result = []
    for client in clients:
        result.append({
            "username": client.username,
            "email": client.email,
            "subscription_id": client.subscription_id,
            "uuid": client.uuid,
            "total_limit_gb": client.total_limit_gb,
            "used_gb": round(client.used_gb, 2),
            "remaining_gb": round(client.remaining_gb, 2),
            "usage_percent": round(client.usage_percent, 2),
            "expiry_days": client.remaining_days,
            "status": client.status,
            "status_persian": client.status_persian,
            "group": client.group,
            "created_at": client.created_at,
            "auto_renew": client.auto_renew,
            "telegram_user_id": client.telegram_user_id,
            "comment": client.comment,
            "reverse_tag": client.reverse_tag,
            "vless_link": generate_vless_link(client.uuid, host, remark=client.username),
            "is_expired": client.is_expired
        })
    
    # مرتب‌سازی بر اساس مصرف
    result.sort(key=lambda x: x["usage_percent"], reverse=True)
    
    return {
        "clients": result,
        "stats": client_manager.get_stats_summary()
    }


@router.get("/{username}")
async def get_client(username: str, _=Depends(require_auth)):
    """دریافت اطلاعات یک کاربر"""
    client = client_manager.get_client(username)
    if not client:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    host = get_host()
    return {
        "username": client.username,
        "email": client.email,
        "subscription_id": client.subscription_id,
        "hysteria_auth": client.hysteria_auth,
        "password": client.password,
        "uuid": client.uuid,
        "total_limit_gb": client.total_limit_gb,
        "used_gb": round(client.used_gb, 2),
        "remaining_gb": round(client.remaining_gb, 2),
        "expiry_days": client.remaining_days,
        "created_at": client.created_at,
        "status": client.status,
        "auto_renew": client.auto_renew,
        "telegram_user_id": client.telegram_user_id,
        "comment": client.comment,
        "reverse_tag": client.reverse_tag,
        "group": client.group,
        "vless_link": generate_vless_link(client.uuid, host, remark=client.username),
        "is_expired": client.is_expired
    }


@router.post("/")
async def create_client(request: Request, _=Depends(require_auth)):
    """ایجاد کاربر جدید"""
    body = await request.json()
    
    # اعتبارسنجی
    if not body.get("username"):
        raise HTTPException(status_code=400, detail="نام کاربری الزامی است")
    
    # بررسی تکراری نبودن
    if client_manager.get_client(body["username"]):
        raise HTTPException(status_code=400, detail="نام کاربری تکراری است")
    
    try:
        client = client_manager.create_client(body)
        return {"ok": True, "client": client.username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{username}")
async def update_client(username: str, request: Request, _=Depends(require_auth)):
    """بروزرسانی کاربر"""
    body = await request.json()
    
    client = client_manager.update_client(username, body)
    if not client:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    return {"ok": True, "client": client.username}


@router.delete("/{username}")
async def delete_client(username: str, _=Depends(require_auth)):
    """حذف کاربر"""
    if not client_manager.delete_client(username):
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return {"ok": True}


@router.post("/{username}/reset")
async def reset_client_usage(username: str, _=Depends(require_auth)):
    """ریست مصرف کاربر"""
    client = client_manager.reset_usage(username)
    if not client:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return {"ok": True, "message": "مصرف با موفقیت ریست شد"}


@router.post("/{username}/add-traffic")
async def add_traffic_to_client(username: str, request: Request, _=Depends(require_auth)):
    """افزودن ترافیک به کاربر"""
    body = await request.json()
    gb = float(body.get("gb", 0))
    
    if gb <= 0:
        raise HTTPException(status_code=400, detail="مقدار ترافیک باید بیشتر از 0 باشد")
    
    client = client_manager.add_traffic(username, gb)
    if not client:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    return {"ok": True, "new_limit": client.total_limit_gb}


@router.post("/{username}/toggle-status")
async def toggle_client_status(username: str, request: Request, _=Depends(require_auth)):
    """تغییر وضعیت کاربر (فعال/غیرفعال)"""
    body = await request.json()
    new_status = body.get("status", "active")
    
    client = client_manager.update_client(username, {"status": new_status})
    if not client:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    return {"ok": True, "status": client.status}


@router.get("/stats/summary")
async def get_clients_stats(_=Depends(require_auth)):
    """گرفتن خلاصه آمار کاربران"""
    return client_manager.get_stats_summary()
