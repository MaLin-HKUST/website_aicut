# A 机器重装系统完整 Runbook

> **版本**: v1.0
> **编写日期**: 2026-04-24
> **适用机器**: A 机器 (14.103.249.104)
> **目标**: 重装系统后，按本手册执行可 100% 恢复所有服务
> **状态**: 待执行

---

## 0. 决策记录 (Decision Log)

| # | 决策 | 原因 |
|---|------|------|
| 1 | 重装而非清理 | 入侵者获取 root，存在内核级/隐藏后门，`/tmp/.XIN-unix` 反复复活，curl/wget/python 被 kill |
| 2 | Worker 机器不重装 | CPU/进程/crontab/SSH 全部干净，Gateway + tunnel 正常 |
| 3 | Git 代码真理源 | 本地 bare repo + 本地工作目录已 push 最新 feature 分支 |
| 4 | PostgreSQL 无需恢复数据 | candidate PG 5 张表全部为空，只需恢复 schema |
| 5 | SQLite 需恢复 | 有真实业务数据 (327KB) |
| 6 | 前端 runtime 复用 | 已有的 .tgz 可直接解压运行，无需重新 build |

---

## 1. 资产清单 (Inventory)

### 1.1 备份资产位置

所有资产已备份到以下位置：

| 资产类型 | 本地路径 | TOS 路径 | 说明 |
|---------|---------|---------|------|
| Git Bare Repo | `/tmp/aicut_rebuild_backup/website_aicut_repo.git` | `rebuild/2026-04-24/website_aicut_repo.git.tar.gz` | 代码真理源 (4.4MB) |
| 配置文件包 | `/tmp/aicut_rebuild_backup/aicut_configs_20260424.tgz` | `rebuild/2026-04-24/aicut_configs_20260424.tgz` | docker-compose, nginx, .env (30KB) |
| 前端 Runtime (维护页) | `/tmp/aicut_rebuild_backup/20260423_fcb3e11_smartcutclosed_web_runtime_clean.tgz` | `rebuild/2026-04-24/runtimes/` | 当前线上版本 (~16MB) |
| 前端 Runtime (Taskcard) | `/tmp/aicut_rebuild_backup/smartcut_taskcard_runtime_5050d65.tgz` | `rebuild/2026-04-24/runtimes/` | 新工作台版本 (~16MB) |
| SQLite 数据库 | 内含于 configs 包 | `rebuild/2026-04-24/website_aicut.db` | 业务数据 (327KB) |
| SSL 证书 | 需重新申请 | - | Let's Encrypt，重装后重新 certbot |
| TOS 现有资产 | - | `autocut-malin` bucket | Smart Cut 产物、历史备份等已存在 |

### 1.2 TOS 凭证

```
TOS_ACCESS_KEY=AKLTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TOS_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TOS_ENDPOINT=https://tos-cn-shanghai.volces.com
TOS_REGION=cn-shanghai
TOS_BUCKET=autocut-malin
```

> **安全提示**: 重装后建议更换 TOS Secret Key

---

## 2. 系统重装步骤

### 2.1 准备工作

1. **记录当前域名 DNS 解析**: `xiaomajianji.cn` -> `14.103.249.104`
2. **保存 SSL 证书** (如果可能): `/etc/letsencrypt/live/xiaomajianji.cn/`
3. **通知 Worker 机器**: 重装期间 Worker 会无法连接，需告知

### 2.2 重装操作系统

```bash
# 通过云服务商控制台重装系统
# 推荐镜像: Ubuntu 22.04 LTS
# 确保选择 "保留数据盘" 选项（如果有独立数据盘）
```

### 2.3 重装后首次登录

```bash
# 使用云服务商提供的初始密码登录
ssh root@14.103.249.104

# 立即修改 root 密码
passwd

# 创建用户 malin
useradd -m -s /bin/bash malin
usermod -aG sudo malin
passwd malin

# 配置 SSH (禁用密码登录，只用密钥)
mkdir -p /home/malin/.ssh
cat > /home/malin/.ssh/authorized_keys << 'EOF'
# 填入你的公钥
EOF
chmod 700 /home/malin/.ssh
chmod 600 /home/malin/.ssh/authorized_keys
chown -R malin:malin /home/malin/.ssh

# 编辑 /etc/ssh/sshd_config
sed -i 's/#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd
```


---

## 3. 基础环境安装

### 3.1 系统更新和必要包

```bash
# 以 malin 用户登录
ssh malin@14.103.249.104

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y \
    curl wget git vim htop net-tools \
    python3 python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    tmux
```

### 3.2 Docker 安装

```bash
# 安装 Docker
sudo apt-get install -y ca-certificates gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 将 malin 加入 docker 组
sudo usermod -aG docker malin
newgrp docker

# 验证
docker --version
docker compose version
```

### 3.3 Node.js 安装

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# 安装 Node.js 20
nvm install 20
nvm use 20
nvm alias default 20

node --version  # v20.x.x
npm --version
```

### 3.4 Python 环境

```bash
# Ubuntu 22.04 自带 Python 3.10
python3 --version  # 应 >= 3.10

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

---

## 4. 代码恢复

### 4.1 关键发现

**Git Remote 是本地 Bare Repo** (`/home/malin/website_aicut_repo.git`)，无远程 GitHub/GitLab 托管。重装后必须恢复此 bare repo，否则所有 feature 分支历史丢失。

### 4.2 恢复 Bare Repo

```bash
cd /home/malin

# 方法1: 从本地开发机 scp 恢复 (推荐)
# 在本地机器执行:
# scp -r /tmp/aicut_rebuild_backup/website_aicut_repo.git malin@14.103.249.104:/home/malin/

# 方法2: 从 TOS 下载 (如果已上传)
# python3 << 'PYEOF'
# import tos
# client = tos.TosClient('AKLT...', '5efa...', 'https://tos-cn-shanghai.volces.com', 'cn-shanghai')
# client.get_object_to_file('autocut-malin', 'rebuild/2026-04-24/website_aicut_repo.git.tar.gz', '/tmp/repo.tar.gz')
# PYEOF
# tar xzf /tmp/repo.tar.gz -C /home/malin/
```

### 4.3 克隆工作目录

```bash
cd /home/malin

# 主项目 (legacy)
git clone /home/malin/website_aicut_repo.git website_aicut

# Taskcard Refactor Live
git clone /home/malin/website_aicut_repo.git website_aicut_taskcard_refactor_live
cd website_aicut_taskcard_refactor_live
git checkout feature/smart-cut-taskcard-refactor

# Refactor Integration
git clone /home/malin/website_aicut_repo.git website_aicut_refactor_integration
cd /home/malin/website_aicut_refactor_integration
git checkout feature/smart-cut-workspace-refactor-integration
```

### 4.4 前端 Runtime 部署目录

```bash
# 创建 releases 目录结构
mkdir -p /home/malin/website_aicut_prod/releases
mkdir -p /home/malin/website_aicut_prod/current
```


---

## 5. 服务部署

### 5.1 配置文件恢复

```bash
cd /home/malin/website_aicut

# 从备份恢复 docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: "3.3"

services:
  api:
    image: website_aicut-api:sqlite-admin
    environment:
      DATABASE_URL: sqlite:////data/website_aicut.db
      ADMIN_USERNAME: admin
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:-Malin123456}
      SESSION_SECRET: ${SESSION_SECRET:-change-this-secret}
      MINIMAX_AUDIO_API_KEY: ${MINIMAX_AUDIO_API_KEY:-}
      MINIMAX_AUDIO_GROUP_ID: ${MINIMAX_AUDIO_GROUP_ID:-}
      MINIMAX_TTS_VOICE_ID: ${MINIMAX_TTS_VOICE_ID:-}
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - /home/malin/website_aicut/data:/data
    restart: unless-stopped

  web:
    image: website_aicut-web:admin
    environment:
      INTERNAL_API_BASE_URL: http://api:8000
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      - api
    restart: unless-stopped
EOF

# 恢复 .env
cat > .env << 'EOF'
POSTGRES_DB=website_aicut
POSTGRES_USER=website_aicut
POSTGRES_PASSWORD=website_aicut
ADMIN_PASSWORD=Malin123456
SESSION_SECRET=change-this-secret

MINIMAX_TTS_VOICE_ID=moss_audio_623373aa-dd87-11f0-9536-6699b2fade72
MINIMAX_AUDIO_API_KEY=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLpqazpup8iLCJVc2VyTmFtZSI6IkF1dG8gdGV4dCB0byBzcGVlY2ggZ2VuZXJhdGlvbiIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTU3NTg2MDcwNTM1MTUyNDUzIiwiUGhvbmUiOiIiLCJHcm91cElEIjoiMTk1NzU4NTkyNDk4ODYwNTI1NCIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6Im1hbGluLmh1c3RAZ21haWwuY29tIiwiQ3JlYXRlVGltZSI6IjIwMjUtMTItMjYgMTE6MDM6NTciLCJUb2tlblR5cGUiOjEsImlzcyI6Im1pbmltYXgifQ.QZPxogQPyCvynjVmhpi_oDXgxF7GlmDHl1vxq28wijuV6lZNdbz_NqcKWaXb4Zl5KynilbePiCzCrV6TcKJWgYBPZjFYRJXXpVcIXEwzRkKpi0HyHkYFyROux_uf4yGPbS9bish0uyrqrdS2uEKbNe-3X06C4vqSxQJATHVW1tXTCLjymeEmHEu_DYn6auJqY7rv1yjPNidQrY6LhFS3zxQoZ9GbShCdNEoGOGZyUPnFd2MONPkL5FxF1GNnLhfQ5hKIdGFqFfBYI2qSH-WdxSCAV0UaTqpwHpuFOYl4i-4HZ9jH6e2Ju2PO8UeRfVn77aCa5t2CkmE38tqV5EZDKw
EOF

# 恢复 SQLite 数据
mkdir -p /home/malin/website_aicut/data
cp /path/to/backup/website_aicut.db /home/malin/website_aicut/data/
```

### 5.2 Legacy Docker 服务启动

```bash
cd /home/malin/website_aicut

# 需要重建 Docker 镜像 (因为镜像也在 A 机器本地)
# 如果有镜像备份:
# docker load < /path/to/website_aicut-api-sqlite-admin.tar
# docker load < /path/to/website_aicut-web-admin.tar

# 或者从代码重新构建 (需要 Dockerfile)
# docker build -t website_aicut-api:sqlite-admin -f docker/Dockerfile.api .
# docker build -t website_aicut-web:admin -f docker/Dockerfile.web .

# 启动 Legacy 服务
docker compose up -d

# 验证
docker ps | grep website_aicut
curl -s http://127.0.0.1:8000/health || echo "Legacy API 未响应"
```

> **注意**: Legacy Docker 镜像 (`website_aicut-api:sqlite-admin`, `website_aicut-web:admin`) 也在 A 机器本地。重装后需要重新构建或从备份恢复。如果 Dockerfile 在代码仓库中，可以直接重新 build。

### 5.3 Candidate PostgreSQL 启动

```bash
# 启动 candidate PostgreSQL (用于 Scheduler 和 Candidate API)
docker run -d \
    --name a-machine-phase5-postgres \
    -p 55433:5432 \
    -e POSTGRES_USER=scheduler \
    -e POSTGRES_PASSWORD=scheduler \
    -e POSTGRES_DB=scheduler \
    -v /home/malin/postgres-data:/var/lib/postgresql/data \
    --restart unless-stopped \
    postgres:16-alpine \
    -p 55433
```

> **注意**: PG 数据为空，只需初始化 schema。如果有 schema dump，可以恢复。

### 5.4 Candidate Scheduler 启动

```bash
cd /home/malin/website_aicut_refactor_integration

# 创建虚拟环境并安装依赖
uv venv .venv313 --python 3.10
source .venv313/bin/activate
uv pip install -e .

# 或者使用 requirements.txt
# uv pip install -r requirements.txt

# 启动 Scheduler (Docker 方式)
docker run -d \
    --name a-machine-phase5-scheduler \
    --network host \
    -e TOS_MODE=real \
    -e TOS_ENDPOINT=https://tos-cn-shanghai.volces.com \
    -e TOS_REGION=cn-shanghai \
    -e TOS_BUCKET=autocut-malin \
    -e TOS_ACCESS_KEY=AKLTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
    -e TOS_SECRET_KEY=TOS_SECRET_KEY_PLACEHOLDER \
    -e SCHEDULER_DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55433/scheduler \
    --restart unless-stopped \
    a-scheduler:0415-af30ae1 \
    python -m apps.scheduler.main

# 或者本地运行 (推荐开发和调试)
# cd /home/malin/website_aicut_taskcard_refactor_live
# source .venv313/bin/activate
# TOS_MODE=real TOS_BUCKET=autocut-malin ... python -m apps.scheduler.main
```

> **注意**: Scheduler Docker 镜像 (`a-scheduler:0415-af30ae1`) 也是本地构建的，需要重新 build 或从备份恢复。

### 5.5 Candidate API 启动

```bash
# Docker 方式
docker run -d \
    --name a-machine-phase5-api \
    --network host \
    -e TOS_ACCESS_KEY=AKLTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
    -e TOS_SECRET_KEY=TOS_SECRET_KEY_PLACEHOLDER \
    -e DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55433/scheduler \
    -e SCHEDULER_DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55433/scheduler \
    -e TOS_MODE=real \
    -e TOS_ENDPOINT=https://tos-cn-shanghai.volces.com \
    -e TOS_REGION=cn-shanghai \
    -e TOS_BUCKET=autocut-malin \
    --restart unless-stopped \
    a-scheduler:0415-af30ae1 \
    uvicorn apps.api.main:app --host 0.0.0.0 --port 18001

# 或者本地运行 (Taskcard Live API on port 18002)
# 见下方 5.7
```


### 5.6 前端部署 (Next.js Standalone)

```bash
# 部署维护页版本
cd /home/malin/website_aicut_prod/releases
tar xzf /path/to/backup/20260423_fcb3e11_smartcutclosed_web_runtime_clean.tgz
mv 20260423_fcb3e11_smartcutclosed_web_runtime_clean 20260423_fcb3e11_web

# 创建符号链接
ln -sfn /home/malin/website_aicut_prod/releases/20260423_fcb3e11_web /home/malin/website_aicut_prod/current/web

# 部署 Taskcard 版本
tar xzf /path/to/backup/smartcut_taskcard_runtime_5050d65.tgz
# 解压后的目录名根据实际包内结构调整
```

### 5.7 Taskcard Live API 启动脚本

```bash
cat > /home/malin/start_taskcard_api.sh << 'EOF'
#!/usr/bin/env bash
cd /home/malin/website_aicut_taskcard_refactor_live
exec env \
  DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55433/scheduler \
  TOS_MODE=real \
  TOS_BUCKET=autocut-malin \
  TOS_ENDPOINT=https://tos-cn-shanghai.volces.com \
  TOS_REGION=cn-shanghai \
  TOS_ACCESS_KEY=AKLTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  TOS_SECRET_KEY=TOS_SECRET_KEY_PLACEHOLDER \
  /home/malin/website_aicut_refactor_integration/.venv313/bin/python \
  -m uvicorn apps.api.main:app --host 0.0.0.0 --port 18002
EOF
chmod +x /home/malin/start_taskcard_api.sh

# 使用 tmux 启动
tmux new-session -d -s taskcard-api /home/malin/start_taskcard_api.sh
```

### 5.8 Taskcard Web 启动脚本

```bash
cat > /home/malin/start_taskcard_web.sh << 'EOF'
#!/usr/bin/env bash
cd /home/malin/website_aicut_prod/releases/20260423_5050d65_taskcard/web_runtime
exec env \
  PORT=3301 \
  HOSTNAME=127.0.0.1 \
  NODE_ENV=production \
  SMART_CUT_API_BASE_URL=http://127.0.0.1:18002 \
  LEGACY_API_BASE_URL=http://127.0.0.1:8000 \
  node server.js
EOF
chmod +x /home/malin/start_taskcard_web.sh

# 使用 tmux 启动
tmux new-session -d -s taskcard-web /home/malin/start_taskcard_web.sh
```

---

## 6. Nginx 配置

### 6.1 安装并配置 Nginx

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx

# 恢复 nginx 配置
sudo tee /etc/nginx/sites-available/xiaomajianji.cn << 'EOF'
server {
    listen 80;
    server_name xiaomajianji.cn www.xiaomajianji.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name xiaomajianji.cn www.xiaomajianji.cn;

    ssl_certificate /etc/letsencrypt/live/xiaomajianji.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiaomajianji.cn/privkey.pem;
    client_max_body_size 512M;

    location /api/proxy/ {
        proxy_pass http://127.0.0.1:3301/api/proxy/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        send_timeout 600s;
    }

    location /_next/static/ {
        proxy_pass http://127.0.0.1:3301/_next/static/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /welcome {
        proxy_pass http://127.0.0.1:3301/welcome;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /smart-cut {
        proxy_pass http://127.0.0.1:3301/smart-cut;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ^~ /smart-cut/ {
        proxy_pass http://127.0.0.1:3301/smart-cut/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /tasks {
        proxy_pass http://127.0.0.1:3301/tasks;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ^~ /tasks/ {
        proxy_pass http://127.0.0.1:3301/tasks/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /admin/tasks {
        proxy_pass http://127.0.0.1:3301/admin/tasks;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ^~ /admin/tasks/ {
        proxy_pass http://127.0.0.1:3301/admin/tasks/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3301;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/xiaomajianji.cn /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 申请 SSL 证书
sudo certbot --nginx -d xiaomajianji.cn -d www.xiaomajianji.cn --non-interactive --agree-tos -m your-email@example.com

sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```


---

## 7. 系统服务配置

### 7.1 禁用恶意服务

```bash
# 检查并禁用可疑服务
sudo systemctl list-unit-files --type=service | grep -E "irqbalance-ng|unknown|suspicious"

# 如果 irqbalance-ng 是恶意服务 (在本次入侵中发现)
sudo systemctl stop irqbalance-ng
sudo systemctl disable irqbalance-ng
sudo rm -f /lib/systemd/system/irqbalance-ng.service

# 检查所有定时任务
sudo crontab -l
sudo find /var/spool/cron -type f -exec cat {} \;
sudo cat /etc/crontab
sudo ls /etc/cron.d/

# 确保没有恶意 wget/curl 定时任务
```

### 7.2 启用必要服务

```bash
sudo systemctl enable docker
sudo systemctl enable nginx
```

### 7.3 防火墙配置

```bash
# 配置 UFW (如果未安装)
sudo apt-get install -y ufw

sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许 SSH (确保不会把自己锁在外面)
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许内部服务端口 (仅本地访问，不需要开放)
# sudo ufw allow 3301/tcp  # 仅 127.0.0.1，不需要
# sudo ufw allow 8000/tcp  # 仅 127.0.0.1，不需要
# sudo ufw allow 18001/tcp  # 仅 127.0.0.1，不需要
# sudo ufw allow 18002/tcp  # 仅 127.0.0.1，不需要
# sudo ufw allow 55433/tcp  # PostgreSQL，仅 Worker 需要

sudo ufw enable
```

---

## 8. 验证清单 (Verification Checklist)

### 8.1 本地验证

```bash
# 在 A 机器上执行

echo "=== 1. Docker 服务 ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "=== 2. 端口监听 ==="
ss -tlnp | grep -E "3301|8000|18001|18002|55433"

echo "=== 3. Legacy API ==="
curl -s http://127.0.0.1:8000/health || curl -s http://127.0.0.1:8000/

echo "=== 4. Candidate API ==="
curl -s http://127.0.0.1:18001/health || curl -s http://127.0.0.1:18001/

echo "=== 5. Taskcard Live API ==="
curl -s http://127.0.0.1:18002/health || curl -s http://127.0.0.1:18002/

echo "=== 6. 前端 ==="
curl -s -I http://127.0.0.1:3301 | head -5

echo "=== 7. PostgreSQL ==="
PGPASSWORD=scheduler psql -h 127.0.0.1 -p 55433 -U scheduler -d scheduler -c "SELECT COUNT(*) FROM smart_cut_tasks;" 2>/dev/null || echo "PG 未就绪或无表"

echo "=== 8. Nginx ==="
sudo nginx -t
systemctl status nginx --no-pager

echo "=== 9. 进程检查 ==="
ps aux | grep -E "node|uvicorn|python.*scheduler" | grep -v grep
```

### 8.2 公网验证

```bash
# 在本地机器执行

echo "=== 1. 域名解析 ==="
dig xiaomajianji.cn +short

echo "=== 2. HTTPS 首页 ==="
curl -s -o /dev/null -w "%{http_code}" https://xiaomajianji.cn/

echo "=== 3. API 健康检查 ==="
curl -s -o /dev/null -w "%{http_code}" https://xiaomajianji.cn/api/health 2>/dev/null || echo "无健康端点"

echo "=== 4. Smart Cut 页面 ==="
curl -s -o /dev/null -w "%{http_code}" https://xiaomajianji.cn/smart-cut

echo "=== 5. SSL 证书 ==="
echo | openssl s_client -servername xiaomajianji.cn -connect xiaomajianji.cn:443 2>/dev/null | openssl x509 -noout -dates -subject
```

### 8.3 Worker 连接验证

```bash
# 在 Worker 机器 (14.103.63.252) 上执行
echo "=== Worker 连接 A 机器 PG ==="
PGPASSWORD=scheduler psql -h 14.103.249.104 -p 55433 -U scheduler -d scheduler -c "SELECT 1;"

echo "=== Worker Gateway ==="
curl -s http://127.0.0.1:gateway_port/health 2>/dev/null || echo "检查 Gateway 状态"
```

---

## 9. 安全加固

### 9.1 必须执行的安全措施

```bash
# 1. 检查并清理所有 crontab
sudo crontab -r 2>/dev/null || true
sudo find /var/spool/cron -type f -delete 2>/dev/null || true
sudo rm -f /etc/cron.d/*

# 2. 检查 .ssh 目录
ls -la /home/malin/.ssh/
# 删除任何不属于你的公钥

# 3. 检查 sudoers
sudo cat /etc/sudoers.d/* 2>/dev/null

# 4. 检查启动项
ls -la /etc/update-motd.d/
ls -la /etc/profile.d/
cat /etc/rc.local 2>/dev/null

# 5. 检查 /tmp 权限
ls -ld /tmp
# 确保 /tmp 没有可疑文件

# 6. 安装 fail2ban
sudo apt-get install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 7. 更换 TOS Secret Key (强烈建议)
# 登录火山引擎控制台 -> 对象存储 -> 密钥管理 -> 更换 Secret Key
```

### 9.2 监控脚本

```bash
# 创建监控脚本
cat > /home/malin/check_system.sh << 'EOF'
#!/bin/bash
# 系统健康检查脚本

echo "=== $(date) ==="
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "Memory: $(free -h | grep Mem)"
echo "Disk: $(df -h / | tail -1)"

echo ""
echo "Docker Containers:"
docker ps --format "{{.Names}}: {{.Status}}"

echo ""
echo "Services:"
systemctl is-active nginx docker

echo ""
echo "Suspicious Processes:"
ps aux | grep -E "xmrig|miner|BEyBgE|javae|\.XIN" | grep -v grep || echo "None found"

echo ""
echo "Crontab:"
sudo crontab -l 2>/dev/null || echo "Empty"
EOF
chmod +x /home/malin/check_system.sh
```

---

## 10. 已知问题与风险

| # | 问题 | 影响 | 缓解措施 |
|---|------|------|---------|
| 1 | Docker 镜像需重新构建 | Legacy/Candidate 服务无法直接启动 | 确保 Dockerfile 在代码仓库中，或提前导出镜像备份 |
| 2 | Git bare repo 是唯一 remote | 重装后丢失所有分支历史 | 已备份到本地 + TOS |
| 3 | SSL 证书需重新申请 | 重装后 HTTPS 无法使用 | 使用 certbot 自动申请 |
| 4 | PostgreSQL 为空 | 无历史任务数据 | 只需初始化 schema，Worker 会重新注册 |
| 5 | Worker 需重新连接 | 重装期间任务中断 | 通知 Worker 管理员，重启 Worker Gateway |
| 6 | TOS Secret Key 可能泄露 | 入侵者可能获取凭证 | 重装后立即更换 |

---

## 11. 附录

### 11.1 快速恢复命令 (一键执行)

```bash
#!/bin/bash
# save as: restore_a_machine.sh
# 在重装后的 A 机器上以 malin 用户执行

set -e

echo "[1/10] 安装基础依赖..."
sudo apt-get update && sudo apt-get install -y curl wget git vim nginx certbot python3-certbot-nginx tmux

echo "[2/10] 安装 Docker..."
# (Docker 安装命令)

echo "[3/10] 安装 Node.js..."
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20

echo "[4/10] 恢复 Git Repo..."
# scp 或从 TOS 下载 website_aicut_repo.git

echo "[5/10] 克隆代码..."
cd /home/malin
git clone website_aicut_repo.git website_aicut
git clone website_aicut_repo.git website_aicut_taskcard_refactor_live
cd website_aicut_taskcard_refactor_live && git checkout feature/smart-cut-taskcard-refactor
git clone website_aicut_repo.git website_aicut_refactor_integration
cd /home/malin/website_aicut_refactor_integration && git checkout feature/smart-cut-workspace-refactor-integration

echo "[6/10] 配置环境..."
cp /path/to/backup/.env /home/malin/website_aicut/
cp /path/to/backup/website_aicut.db /home/malin/website_aicut/data/

echo "[7/10] 启动 Docker 服务..."
cd /home/malin/website_aicut
docker compose up -d

echo "[8/10] 启动 PostgreSQL..."
docker run -d --name a-machine-phase5-postgres -p 55433:5432 \
  -e POSTGRES_USER=scheduler -e POSTGRES_PASSWORD=scheduler -e POSTGRES_DB=scheduler \
  --restart unless-stopped postgres:16-alpine -p 55433

echo "[9/10] 启动前端和 API..."
# (启动脚本命令)

echo "[10/10] 配置 Nginx..."
sudo certbot --nginx -d xiaomajianji.cn --non-interactive --agree-tos -m your-email@example.com

echo "恢复完成！请执行验证清单。"
```

### 11.2 联系信息

- **A 机器 IP**: 14.103.249.104
- **Worker IP**: 14.103.63.252
- **域名**: xiaomajianji.cn
- **TOS Bucket**: autocut-malin @ tos-cn-shanghai.volces.com
- **前端账号**: zhangyongqiang/123456, rbzj/123456

### 11.3 备份文件清单

```
本地备份目录: /tmp/aicut_rebuild_backup/
├── website_aicut_repo.git/              # Git Bare Repo (4.4MB)
├── aicut_configs_20260424.tgz           # 配置文件包 (30KB)
│   ├── docker-compose.yml
│   ├── docker-compose-ports.yml
│   ├── docker-compose.env
│   ├── .env.example
│   ├── nginx_xiaomajianji.cn.conf
│   └── website_aicut.db
├── 20260423_fcb3e11_smartcutclosed_web_runtime_clean.tgz  # 维护页 (16MB)
└── smartcut_taskcard_runtime_5050d65.tgz                  # Taskcard 页 (16MB)
```

---

> **最后更新**: 2026-04-24  
> **编写者**: Kimi Code CLI  
> **审核状态**: 待人工审核

