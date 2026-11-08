FROM python:3.11-slim

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/vnstock:${PYTHONPATH}" \
    PORT=8502

WORKDIR /app

# Cài đặt các gói hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Sao chép và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir qrcode pillow

# Sao chép toàn bộ mã nguồn
COPY . .

# Expose cổng Streamlit
EXPOSE 8502

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8502/_stcore/health || exit 1

# Khởi chạy Streamlit độc lập
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8502", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
