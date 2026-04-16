# Smart Cut Worker Gateway Dockerfile

FROM python:3.10-slim

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

# 设置工作目录
WORKDIR /app

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
