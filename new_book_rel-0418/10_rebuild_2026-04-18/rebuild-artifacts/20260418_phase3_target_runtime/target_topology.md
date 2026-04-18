# 2026-04-18 Phase 3 Target Topology

本文回答什么问题：

- 本轮重建完成后，A 机器最终要保留什么
- Worker 机器最终要保留什么
- 哪些对象只是过渡保留
- 哪些对象最终必须退出

## 1. 最终目标拓扑

### A 机器

长期正式保留：

- `nginx`
  - 唯一公网入口
  - 域名：`xiaomajianji.cn`
- `A-Web`
  - 唯一正式前端运行面
  - 不再长期并存 `3000` 与 `3001`
- `A-Biz API`
  - 网站业务 API
  - 承担 `admin / auth / 网站业务`
- `SQLite`
  - 只服务 `admin / auth / 网站主数据`
- `A-Scheduler API`
  - 调度侧 API
- `A-Scheduler Runtime`
  - 调度器
- `PostgreSQL`
  - 只服务调度中心
- `A-TOS Tools`
  - A 机器正式 TOS 上传下载工具链
  - 目标目录：`/home/malin/website_aicut_tools/tos_uploader/`

### Worker 机器

长期正式保留：

- `Worker Gateway`
  - 与 A 机器调度中心交互
  - 负责设备注册、心跳、领任务、TOS 下载/上传
- `Smart Cut Worker`
  - 纯算法运行面
  - 不碰调度真相库
  - 不直接承担 TOS 逻辑

### TOS

长期正式保留的角色：

- 跨机器输入输出传递层
- 备份归档层
- release bundle 传递层

## 2. 端口与运行面原则

### A 机器最终允许长期存在的逻辑端口

- 前端：唯一一套正式端口
- 网站 API：唯一一套正式端口
- 调度 API：唯一一套正式端口
- PostgreSQL：唯一一套正式端口

### A 机器不再允许长期并存的形态

- `3000 + 3001` 双前端长期并存
- 旧网站 API 与新网站 API 无边界并存
- Worker Gateway 常驻在 A 机器
- Smart Cut Worker 常驻在 A 机器

## 3. 数据边界

### SQLite

只承载：

- admin
- auth
- 网站主数据

不得承载：

- 调度任务真相
- Worker 设备状态
- Smart Cut 任务流转状态

### PostgreSQL

只承载：

- 调度任务
- 设备状态
- Smart Cut 任务与编辑稿状态

不得承载：

- admin
- auth
- 网站主数据

## 4. 正式保留 / 过渡保留 / 必须退出

### 正式保留

- A 机器：
  - `nginx`
  - 正式前端
  - 网站 API
  - SQLite
  - 调度 API
  - Scheduler Runtime
  - PostgreSQL
  - 正式 TOS 工具链
- Worker：
  - Worker Gateway
  - Smart Cut Worker
- TOS：
  - 业务文件
  - 备份文件
  - release bundle

### 过渡保留

- `release_0415_slot`
  - 直到新正式运行面切流成功前保留
- 旧 `3000` 前端线
  - 直到新正式前端和回滚锚点都稳定
- A 机器上的 `release0415_worker`
  - 直到 Worker 机器正式接管
- `/tmp/tos_uploader_runtime`
  - 直到正式迁入 `/home/malin/website_aicut_tools/tos_uploader/`

### 最终必须退出

- A 机器上的长期 Worker 运行面
- A 机器上的长期算法执行运行面
- 双前端长期并存
- 无主测试容器
- 无主镜像
- 失败的 scp 中间物
- 不再承担正式职责的历史目录

## 对 Agent 的直接指令

- 不要再把 A 机器理解成执行机。
- 不要在没有完成正式迁移前删除 `/tmp/tos_uploader_runtime`。
- 新链路稳定后，除了正式运行面、正式工具、正式配置、正式数据、正式回滚锚点，其余对象都应进入清理范围。
