FROM python:3.11-slim

WORKDIR /app

# نصب curl برای healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# مهم: expose پورتی که Railway استفاده می‌کند
EXPOSE 8080

# Healthcheck با پورت صحیح
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health/simple || exit 1

# استفاده از پورت 8080 (پورت پیش‌فرض Railway)
CMD uvicorn main:app --host 0.0.0.0 --port 8080 --workers 2
