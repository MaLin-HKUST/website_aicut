# Smart Cut Worker Gateway Dockerfile

FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (包含 FFmpeg 等视频处理工具)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY worker/requirements.txt ./requirements.txt

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY apps/ ./apps/
COPY worker/ ./worker/
COPY configs/ ./configs/

# 创建工作目录
RUN mkdir -p /app/data/db /fake-tos /data/worker-jobs

# 复制启动脚本
COPY worker/docker-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 健康检查
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -m worker.main --check || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
