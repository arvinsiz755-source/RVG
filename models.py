# models.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import json


class ClientData(BaseModel):
    """مدل داده کاربر / کلاینت"""
    username: str  # نام کاربری
    email: str  # ایمیل
    subscription_id: str  # آیدی اشتراک (UUID)
    password: str  # رمز عبور (اختیاری)
    hysteria_auth: Optional[str] = None  # احراز هویت Hysteria
    uuid: str  # UUID لینک VLESS
    total_limit_gb: float  # سقف ترافیک بر حسب گیگ
    used_gb: float  # ترافیک مصرف شده
    expiry_days: int  # تعداد روز اعتبار
    created_at: str  # تاریخ ایجاد
    last_reset: str  # آخرین تاریخ ریست
    status: str  # active, ended, offline, disabled
    auto_renew: bool = False  # تمدید خودکار
    telegram_user_id: Optional[int] = None  # آیدی تلگرام
    comment: Optional[str] = None  توضیحات
    reverse_tag: Optional[str] = None  # تگ معکوس
    group: str = "default"  # گروه کاربری (Sajdaj, Seyed, ...)
    
    def to_dict(self):
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
    
    @property
    def remaining_gb(self) -> float:
        """ترافیک باقی‌مانده"""
        return max(0, self.total_limit_gb - self.used_gb)
    
    @property
    def usage_percent(self) -> float:
        """درصد مصرف"""
        if self.total_limit_gb == 0:
            return 0
        return min(100, (self.used_gb / self.total_limit_gb) * 100)
    
    @property
    def is_expired(self) -> bool:
        """آیا منقضی شده؟"""
        created = datetime.fromisoformat(self.created_at)
        expiry_date = created.replace(day=created.day + self.expiry_days)
        return datetime.now() > expiry_date
    
    @property
    def remaining_days(self) -> int:
        """روزهای باقی‌مانده"""
        created = datetime.fromisoformat(self.created_at)
        expiry_date = created.replace(day=created.day + self.expiry_days)
        delta = expiry_date - datetime.now()
        return max(0, delta.days)
    
    @property
    def status_persian(self) -> str:
        """وضعیت به فارسی"""
        status_map = {
            "active": "فعال",
            "ended": "پایان یافته",
            "offline": "آفلاین",
            "disabled": "غیرفعال"
        }
        return status_map.get(self.status, "نامشخص")
    
    def generate_vless_link(self, host: str) -> str:
        """تولید لینک VLESS"""
        from helpers import generate_vless_link
        return generate_vless_link(self.uuid, host, remark=f"{self.username}")
