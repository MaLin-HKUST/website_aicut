# Smart Cut Worker Gateway Dockerfile

FROM python:3.10-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

# 设置工作目录
WORKDIR /app

# 系统依赖：算法链需要 ffmpeg / ffprobe 做音频提取与媒体探测
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

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
