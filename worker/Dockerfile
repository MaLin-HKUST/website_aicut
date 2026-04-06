FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt /tmp/worker-requirements.txt
RUN pip install --no-cache-dir -r /tmp/worker-requirements.txt

COPY worker/entrypoint.sh /usr/local/bin/smart-cut-entrypoint
COPY worker/run_manual_cujian_test.sh /usr/local/bin/run-manual-cujian-test
RUN chmod +x /usr/local/bin/smart-cut-entrypoint /usr/local/bin/run-manual-cujian-test

ENTRYPOINT ["smart-cut-entrypoint"]
CMD ["sleep", "infinity"]
