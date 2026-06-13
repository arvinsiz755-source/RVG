#!/bin/bash
# entrypoint.sh - تنظیم خودکار متغیرهای محیطی برای سرعت بالا

echo "🔄 تنظیم خودکار متغیرهای محیطی برای سرعت بالا..."

# تنظیم متغیرها اگر از قبل تنظیم نشده باشند
export UVICORN_WORKERS=${UVICORN_WORKERS:-2}
export UVICORN_LIMIT_CONCURRENCY=${UVICORN_LIMIT_CONCURRENCY:-2000}
export PYTHONOPTIMIZE=${PYTHONOPTIMIZE:-2}
export WEB_CONCURRENCY=${WEB_CONCURRENCY:-2}

# تنظیمات حافظه
export UVICORN_BACKLOG=${UVICORN_BACKLOG:-4096}
export UVICORN_TIMEOUT_KEEP_ALIVE=${UVICORN_TIMEOUT_KEEP_ALIVE:-30}

# تنظیمات لاگ (کاهش برای سرعت)
export UVICORN_LOG_LEVEL=${UVICORN_LOG_LEVEL:-warning}

# نمایش متغیرهای تنظیم شده
echo "✅ متغیرهای تنظیم شده:"
echo "   - UVICORN_WORKERS: $UVICORN_WORKERS"
echo "   - UVICORN_LIMIT_CONCURRENCY: $UVICORN_LIMIT_CONCURRENCY"
echo "   - PYTHONOPTIMIZE: $PYTHONOPTIMIZE"
echo "   - UVICORN_BACKLOG: $UVICORN_BACKLOG"

# اجرای uvicorn با متغیرهای تنظیم شده
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${UVICORN_WORKERS} \
    --loop uvloop \
    --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY} \
    --backlog ${UVICORN_BACKLOG} \
    --log-level ${UVICORN_LOG_LEVEL}
