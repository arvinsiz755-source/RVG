FROM python:3.13-slim

WORKDIR /app

# بهینه‌سازی برای سرعت
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    UVICORN_WORKERS=4 \
    WEB_CONCURRENCY=4 \
    UVICORN_LIMIT_CONCURRENCY=1000 \
    UVICORN_BACKLOG=2048

# نصب وابستگی‌های سیستمی
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل requirements
COPY requirements.txt .

# نصب وابستگی‌های پایتون
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . .

# کپی و تنظیم entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ایجاد کاربر غیر روت برای امنیت بیشتر
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# استفاده از entrypoint
ENTRYPOINT ["/entrypoint.sh"]
