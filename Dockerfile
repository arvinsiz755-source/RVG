FROM python:3.13-slim

WORKDIR /app

# تنظیم پیش‌فرض متغیرهای محیطی - اینها خودکار اعمال می‌شوند
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    UVICORN_WORKERS=2 \
    UVICORN_LIMIT_CONCURRENCY=2000 \
    UVICORN_BACKLOG=4096 \
    UVICORN_LOG_LEVEL=warning

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# کپی و تنظیم entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ایجاد کاربر غیر روت
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# استفاده از entrypoint
ENTRYPOINT ["/entrypoint.sh"]
