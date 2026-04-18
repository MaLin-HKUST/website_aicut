# 阶段 5 A 机器候选稳定态日志

阶段：`20260419_phase5_a_machine_candidate`

## 本阶段目标

在不覆盖旧链路的前提下，为 A 机器建立一套新的候选运行面：

- 保留旧 `8000` legacy SQLite/admin/auth API
- 在新部署根 `/home/malin/website_aicut_prod` 下启动：
  - 候选 PostgreSQL
  - 候选 smart-cut API
  - 候选 scheduler runtime
  - 候选 web
- 把 TOS uploader 工具链转正到正式工具目录

## 本阶段实际完成情况

### 1. 新部署根建立

候选部署根已经在 A 机器建立：

- `/home/malin/website_aicut_prod`

本轮实际使用的子目录：

- `/home/malin/website_aicut_prod/web`
- `/home/malin/website_aicut_prod/postgres-data`
- `/home/malin/website_aicut_prod/manifests`
- `/home/malin/website_aicut_prod/tools/tos_uploader`

### 2. 候选 smart-cut 中心侧启动

本轮最终稳定起来的候选容器：

- `a-machine-phase5-postgres`
- `a-machine-phase5-api`
- `a-machine-phase5-scheduler`

使用端口：

- PostgreSQL：`55433`
- smart-cut API：`18001`
- candidate web：`3301`

### 3. 候选 web 启动

候选 web 最终运行在：

- `127.0.0.1:3301`

这轮最终采用的是：

- 本地 `apps/web` 构建
- 本地打包 runtime
- 上传到 A 机器
- A 机器解包并启动

这样绕开了远端重复 `next build` 的资源波动问题。

### 4. TOS 工具链转正

本地 `tos_uploader` 代码已复制到：

- `/home/malin/website_aicut_prod/tools/tos_uploader`

这意味着阶段 2 中还停留在 `/tmp/tos_uploader_runtime` 的临时工具链，现在已经有正式落点。

## 本阶段遇到的问题与处理

### 问题 1：远端打包 runtime 被系统杀掉

现象：

- `package_web_runtime.sh` 在 A 机器压缩 runtime 时被 `Killed`

处理：

- 改成远端直接落 runtime 目录
- 后续又改为在本地构建 runtime，再上传到 A 机器

### 问题 2：远端 `docker build` 拉基础镜像超时

现象：

- `docker build -f apps/api/Dockerfile` 访问 `registry-1.docker.io` 超时

处理：

- 阶段 5 候选 smart-cut API/scheduler 改为复用 A 机器已有镜像：
  - `a-scheduler:0415-af30ae1`

### 问题 3：candidate scheduler 首次启动退出

现象：

- scheduler 在 fresh database 上报：
  - `duplicate key value violates unique constraint "pg_type_typname_nsp_index"`

判断：

- 更像 API 和 scheduler 并发第一次建库时的竞态，而不是长期 schema 损坏

处理：

- 先让 candidate API 初始化数据库并健康
- 然后单独重启 candidate scheduler
- 重启后 scheduler 正常进入循环

### 问题 4：candidate web 出现双 listener

现象：

- `3301` 一度同时有：
  - `127.0.0.1:3301`
  - `192.168.92.197:3301`

处理：

- 删除旧的残留 listener
- 最终仅保留当前候选 web 的 `127.0.0.1:3301`

## 验证结果

已验证：

- candidate smart-cut API：
  - `/health` 返回 `{"status":"healthy"}`
- candidate web：
  - `/login` 返回 `200 OK`
- candidate scheduler：
  - 日志显示 `Scheduler loop started with 5s interval`
- candidate 容器三件套全部存活
- candidate 端口绑定存在
- candidate login 页面命中了当前版本文案标记

对应证据文件：

- `candidate_containers.txt`
- `candidate_ports.txt`
- `candidate_health.txt`
- `candidate_login_markers.txt`
- `tos_toolchain_files.txt`
- `a_machine_stable_anchor_2_manifest.json`

## 本阶段结论

阶段 5 可以视为完成：

- A 机器新部署根已建立
- 候选中心侧（PostgreSQL + smart-cut API + scheduler）已建立
- 候选 web 已建立
- 候选运行面没有覆盖旧正式链路
- TOS uploader 已转入正式工具目录

当前仍未做的是：

- nginx 仍未切到 candidate web
- Worker 仍未接回候选中心侧
- 主链路闭环尚未开始验收

这些属于后续阶段 6/7 的工作，而不是阶段 5 内部未完成项。
