# PaddleOCR Web Service Dockerfile
# ================================

FROM python:3.10-slim

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 創建工作目錄
WORKDIR /app

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 複製應用程式
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# 創建必要目錄
RUN mkdir -p uploads logs

# 設定權限
RUN chmod -R 755 /app

# 暴露埠號
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 啟動命令
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
