# 阶段 6：Worker 接回候选中心侧执行报告

时间：2026-04-19

## 结论

阶段 6 已完成。

当前状态应定义为：

- Worker 接回：已完成
- 设备注册与心跳：已完成
- 调度任务分配：已完成
- 真实 TOS 输入下载：已完成
- 真实 TOS 输出上传：已完成
- `upload-direct`：已恢复

## 本阶段完成了什么

### 1. Worker 侧正式候选目录已建立

Worker 机器候选部署根：

- `/home/malin/website_aicut_worker_prod`

当前保留的关键子目录：

- `code/website_aicut`
- `code/aicut2602`
- `tools/tos_uploader`
- `tools/remote_build_worker_candidate.sh`
- `tools/worker_open_a_candidate_tunnel.sh`
- `logs/`
- `manifests/`
- `worker_data/`

### 2. Worker 与 A candidate 中心侧已重新接通

由于 Worker 机器无法直接访问 A candidate 的：

- `14.103.249.104:55433`
- `14.103.249.104:18001`
- `192.168.92.197:55433`
- `192.168.92.197:18001`

阶段 6 采用了 Worker 本机 SSH tunnel：

- `127.0.0.1:65433 -> A:127.0.0.1:55433`
- `127.0.0.1:61001 -> A:127.0.0.1:18001`

这条 tunnel 在阶段 6 内保持可用，Worker Gateway 已持续通过它连接 candidate PostgreSQL 与 candidate API。

### 3. Worker Gateway 已正式跑在 Worker 机器

候选容器：

- `worker1-phase6-gateway`

关键环境：

- `DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@127.0.0.1:65433/scheduler`
- `API_BASE_URL=http://127.0.0.1:61001`
- `USE_FAKE_TOS=false`
- `TOS_BUCKET=autocut-malin`
- `ALGORITHM_IMAGE=a-scheduler:0415-af30ae1`

### 4. Worker 已注册并持续发心跳

在 A candidate PostgreSQL 中，设备记录已稳定存在：

- `worker_id = worker1-phase6`
- `worker_name = Worker 1 Phase 6`
- `status = IDLE`
- `heartbeat_at` 持续刷新

这说明执行面已经从 A 机器接回 Worker 机器。

## 阶段 6 中解决的关键阻塞

### 阻塞 1：真实 TOS 适配层错误

阶段 6 初始状态下：

- candidate API 的 `upload-direct` 返回 `403 Forbidden`
- Worker 下载真实 TOS 输入对象时返回 `403 Forbidden`

根因不在调度或 Worker 注册，而在当前仓库的 `apps/services/tos_service.py` 真实模式仍停留在 `boto3` / S3 兼容层。

修复方式：

- 将 `apps/services/tos_service.py` 的 `RealTOSClient` 切换到火山官方 `tos` SDK
- API 与 Worker 运行环境都补装 `tos>=2.0.0`
- 将修复后的 `apps/services/tos_service.py` 热补到：
  - `a-machine-phase5-api`
  - `worker1-phase6-gateway` 所挂载的代码根

### 阻塞 2：Worker 默认 bucket 错误

阶段 6 初期 Worker 仍默认读取 `smart-cut` bucket。

修复方式：

- `worker/services/file_transport.py`
- `worker/processors/base_stage_processor.py`

这两处已改为优先读取环境变量 `TOS_BUCKET`。

### 阻塞 3：candidate API 容器中 route 代码滞后

热修 TOS 后，candidate API 查询详情一度仍报 `500`，原因是：

- 容器内的 `apps/api/routes/tasks.py` 仍是旧版逻辑

修复方式：

- 将当前仓库的 `tasks.py` 热补到 `a-machine-phase5-api`
- 重启 candidate API

## 直接成功证据

### 1. via-TOS analyze 全链路成功

业务任务：

- `3bfab3aa-f648-40a2-96a0-333b25f2b699`

调度任务：

- `b5de5aac-ae47-4b22-8196-f08b372970c8`

Worker 日志已证明：

- 从真实 TOS 下载输入成功
- analyze 产物上传回真实 TOS 成功
- 任务最终推进到：
  - `status = waiting_user`
  - `current_stage = user_select`

### 2. `upload-direct` 已恢复

业务任务：

- `a0e3f1a1-0737-4d32-af47-a65957b6bb67`

当前 `upload-direct` 已能直接把前端上传文件写入真实 TOS，并把任务推进到：

- `status = ready_analyze`
- `current_stage = analyze`

### 3. Worker 真实 TOS 下载日志

在 `worker1-phase6-gateway` 日志中，已经出现：

- `get_object exec httpCode: 200`
- `put_object exec httpCode: 200`
- `head_object exec httpCode: 200`

这说明阶段 6 的真实 TOS 输入输出已经恢复。

## 本阶段涉及的代码与脚本

代码：

- `apps/services/tos_service.py`
- `apps/api/requirements.txt`
- `worker/requirements.txt`
- `worker/services/file_transport.py`
- `worker/processors/base_stage_processor.py`
- `apps/api/routes/tasks.py`

脚本：

- `scripts/rebuild_phase6/remote_build_worker_candidate.sh`
- `scripts/rebuild_phase6/worker_open_a_candidate_tunnel.sh`
- `scripts/rebuild_phase6/a_machine_phase6_smoke.sh`
- `scripts/rebuild_phase6/a_machine_phase6_smoke_via_tos.sh`

## 对下一步的直接指令

阶段 6 已完成，可以进入阶段 7。

后续不需要再把问题归因到：

- Worker 接回失败
- Worker 未注册
- 调度任务未分配
- TOS 读写完全不可用

这些问题都已经在阶段 6 内解决。
