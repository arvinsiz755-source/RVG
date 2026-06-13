# client_manager.py
import json
import os
import uuid as uuid_lib
from datetime import datetime
from typing import List, Optional
from models import ClientData


class ClientManager:
    """مدیریت تمام کاربران / کلاینت‌ها"""
    
    def __init__(self, data_file: str = "clients.json"):
        self.data_file = data_file
        self.clients: dict = {}  # username -> ClientData
        self.load()
    
    def load(self):
        """بارگذاری داده‌ها از فایل JSON"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.clients = {
                        username: ClientData.from_dict(client_data)
                        for username, client_data in data.items()
                    }
            except Exception as e:
                print(f"Error loading clients: {e}")
                self.clients = {}
        else:
            # ایجاد داده‌های نمونه
            self._create_sample_data()
    
    def save(self):
        """ذخیره داده‌ها در فایل JSON"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            data = {
                username: client.to_dict()
                for username, client in self.clients.items()
            }
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _create_sample_data(self):
        """ایجاد داده‌های نمونه (بر اساس تصویر شما)"""
        now = datetime.now().isoformat()
        sample_clients = [
            ClientData(
                username="kiddo-jxl7x2a6",
                email="kiddo@example.com",
                subscription_id="kiddo-jxl7x2a6",
                password="",
                uuid=str(uuid_lib.uuid4()),
                total_limit_gb=31.35,
                used_gb=31.35,
                expiry_days=0,
                created_at=now,
                last_reset=now,
                status="disabled",
                group="Sajdaj,Seyed"
            ),
            ClientData(
                username="nima-gng7xqge",
                email="nima@example.com",
                subscription_id="gzonyd4yxfp5n323",
                password="",
                uuid=str(uuid_lib.uuid4()),
                total_limit_gb=100.0,
                used_gb=46.56,
                expiry_days=24,
                created_at=now,
                last_reset=now,
                status="offline",
                group="Sajdaj,Seyed",
                telegram_user_id=123456789
            ),
            ClientData(
                username="radmehr",
                email="radmehr@example.com",
                subscription_id="gmsow7ai6kqern27",
                password="",
                uuid=str(uuid_lib.uuid4()),
                total_limit_gb=50.0,
                used_gb=0.08094,
                expiry_days=25,
                created_at=now,
                last_reset=now,
                status="offline",
                group="Sajdaj,Seyed"
            ),
            ClientData(
                username="mobin-extra-2g8jj5n4",
                email="mobin@example.com",
                subscription_id="pn9r1116sm18b0qt",
                password="",
                uuid=str(uuid_lib.uuid4()),
                total_limit_gb=100.0,
                used_gb=2.68,
                expiry_days=24,
                created_at=now,
                last_reset=now,
                status="offline",
                group="Sajdaj,Seyed"
            ),
            ClientData(
                username="xfqfeqx",
                email="xfqfeqx@example.com",
                subscription_id="zf18xs645t66e8tu",
                password="",
                uuid=str(uuid_lib.uuid4()),
                total_limit_gb=15.0,
                used_gb=15.04,
                expiry_days=0,
                created_at=now,
                last_reset=now,
                status="ended",
                group="Sajdaj,Seyed"
            ),
        ]
        self.clients = {c.username: c for c in sample_clients}
        self.save()
    
    def get_all_clients(self) -> List[ClientData]:
        """دریافت همه کاربران"""
        return list(self.clients.values())
    
    def get_client(self, username: str) -> Optional[ClientData]:
        """دریافت کاربر با نام کاربری"""
        return self.clients.get(username)
    
    def get_client_by_uuid(self, uuid: str) -> Optional[ClientData]:
        """دریافت کاربر با UUID"""
        for client in self.clients.values():
            if client.uuid == uuid:
                return client
        return None
    
    def create_client(self, client_data: dict) -> ClientData:
        """ایجاد کاربر جدید"""
        client = ClientData(
            username=client_data.get("username"),
            email=client_data.get("email", ""),
            subscription_id=client_data.get("subscription_id", str(uuid_lib.uuid4())[:16]),
            password=client_data.get("password", ""),
            uuid=client_data.get("uuid", str(uuid_lib.uuid4())),
            total_limit_gb=float(client_data.get("total_limit_gb", 50)),
            used_gb=float(client_data.get("used_gb", 0)),
            expiry_days=int(client_data.get("expiry_days", 30)),
            created_at=datetime.now().isoformat(),
            last_reset=datetime.now().isoformat(),
            status=client_data.get("status", "active"),
            auto_renew=client_data.get("auto_renew", False),
            telegram_user_id=client_data.get("telegram_user_id"),
            comment=client_data.get("comment", ""),
            reverse_tag=client_data.get("reverse_tag", ""),
            group=client_data.get("group", "default")
        )
        self.clients[client.username] = client
        self.save()
        return client
    
    def update_client(self, username: str, update_data: dict) -> Optional[ClientData]:
        """بروزرسانی کاربر"""
        client = self.get_client(username)
        if not client:
            return None
        
        for key, value in update_data.items():
            if hasattr(client, key) and value is not None:
                if key in ["total_limit_gb", "used_gb", "expiry_days"]:
                    setattr(client, key, float(value) if value else 0)
                elif key in ["auto_renew"]:
                    setattr(client, key, bool(value))
                else:
                    setattr(client, key, value)
        
        self.save()
        return client
    
    def delete_client(self, username: str) -> bool:
        """حذف کاربر"""
        if username in self.clients:
            del self.clients[username]
            self.save()
            return True
        return False
    
    def reset_usage(self, username: str) -> Optional[ClientData]:
        """ریست مصرف ترافیک"""
        client = self.get_client(username)
        if client:
            client.used_gb = 0
            client.last_reset = datetime.now().isoformat()
            self.save()
        return client
    
    def add_traffic(self, username: str, gb: float) -> Optional[ClientData]:
        """افزودن ترافیک به کاربر"""
        client = self.get_client(username)
        if client:
            client.total_limit_gb += gb
            self.save()
        return client
    
    def get_stats_summary(self) -> dict:
        """گرفتن خلاصه آمار"""
        clients = self.get_all_clients()
        total_traffic = sum(c.total_limit_gb for c in clients)
        used_traffic = sum(c.used_gb for c in clients)
        active_clients = sum(1 for c in clients if c.status == "active" and not c.is_expired)
        
        return {
            "total_clients": len(clients),
            "active_clients": active_clients,
            "total_traffic_gb": round(total_traffic, 2),
            "used_traffic_gb": round(used_traffic, 2),
            "remaining_traffic_gb": round(total_traffic - used_traffic, 2)
        }


# نمونه singleton
client_manager = ClientManager()
