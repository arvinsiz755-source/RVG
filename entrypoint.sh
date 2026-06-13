#!/bin/bash
# entrypoint.sh - تنظیم خودکار متغیرهای محیطی

echo "🔄 تنظیم خودکار متغیرهای محیطی..."

# تنظیم متغیرهای محیطی بهینه برای FastAPI/Uvicorn
export WEB_CONCURRENCY=${WEB_CONCURRENCY:-4}
export UVICORN_WORKERS=${UVICORN_WORKERS:-4}
export PYTHONOPTIMIZE=${PYTHONOPTIMIZE:-2}
export PYTHONDONTWRITEBYTECODE=${PYTHONDONTWRITEBYTECODE:-1}
export PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-1}

# تنظیمات Railway
if [ -n "$RAILWAY_PUBLIC_DOMAIN" ]; then
    echo "✅ Railway domain detected: $RAILWAY_PUBLIC_DOMAIN"
    export HOST=$RAILWAY_PUBLIC_DOMAIN
fi

# تنظیمات حافظه و همزمانی
export UVICORN_LIMIT_CONCURRENCY=${UVICORN_LIMIT_CONCURRENCY:-1000}
export UVICORN_BACKLOG=${UVICORN_BACKLOG:-2048}

# تنظیمات لاگ (برای کاهش لاگ در production)
if [ "$ENVIRONMENT" = "production" ]; then
    export UVICORN_LOG_LEVEL="warning"
else
    export UVICORN_LOG_LEVEL=${UVICORN_LOG_LEVEL:-"info"}
fi

# تنظیمات دیتابیس (اختیاری)
if [ -n "$DATABASE_URL" ]; then
    echo "✅ Database connection configured"
fi

# تنظیمات تلگرام (اختیاری)
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo "✅ Telegram notifications enabled"
fi

# تنظیمات Redis برای کش (اختیاری)
if [ -n "$REDIS_URL" ]; then
    echo "✅ Redis cache enabled"
fi

echo "🚀 متغیرهای محیطی تنظیم شدند:"
echo "   - WEB_CONCURRENCY: $WEB_CONCURRENCY"
echo "   - UVICORN_WORKERS: $UVICORN_WORKERS"
echo "   - LOG_LEVEL: ${UVICORN_LOG_LEVEL:-info}"
echo "   - LIMIT_CONCURRENCY: $UVICORN_LIMIT_CONCURRENCY"

# اجرای دستور اصلی
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${UVICORN_WORKERS} \
    --loop uvloop \
    --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY} \
    --backlog ${UVICORN_BACKLOG} \
    --log-level ${UVICORN_LOG_LEVEL}
