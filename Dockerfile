FROM python:3.11-slim

WORKDIR /app

# فقط نصب curl برای healthcheck (اختیاری)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# از متغیر PORT استفاده می‌کنیم
EXPOSE 8080

# بدون healthcheck در Dockerfile - در Railway تنظیم می‌کنیم
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
