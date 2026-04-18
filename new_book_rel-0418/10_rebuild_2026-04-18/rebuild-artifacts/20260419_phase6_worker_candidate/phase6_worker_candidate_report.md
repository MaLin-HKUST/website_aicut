# 阶段 6：Worker 接回候选中心侧执行报告

时间：2026-04-19

## 结论

阶段 6 已完成到“Worker 接回并能被调度中心识别”的程度，但尚未完成到“analyze 成功产出”的程度。

当前状态应定义为：

- Worker 接回：已完成
- 设备注册与心跳：已完成
- 调度任务分配：已完成
- 真实 TOS 输入下载：阻塞
- analyze 产物生成：阻塞

## 已完成的部分

### 1. Worker 候选部署根已建立

Worker 机器正式候选目录：

- `/home/malin/website_aicut_worker_prod`

其中已落地：

- `code/website_aicut`
- `code/aicut2602`
- `tools/tos_uploader`
- `tools/remote_build_worker_candidate.sh`
- `tools/worker_open_a_candidate_tunnel.sh`
- `logs/`
- `manifests/`
- `worker_data/`

### 2. Worker 与 A 机器 candidate 中心侧已接通

由于 Worker 机器无法直接访问：

- `14.103.249.104:55433`
- `14.103.249.104:18001`
- `192.168.92.197:55433`
- `192.168.92.197:18001`

因此阶段 6 采用了 Worker 本机 SSH tunnel：

- `127.0.0.1:65433 -> A:127.0.0.1:55433`
- `127.0.0.1:61001 -> A:127.0.0.1:18001`

隧道建立成功，验证结果：

- `tunnel_ok 127.0.0.1:65433`
- `tunnel_ok 127.0.0.1:61001`

### 3. Worker Gateway 候选容器已成功启动

容器：

- `worker1-phase6-gateway`

使用的关键配置：

- `DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@127.0.0.1:65433/scheduler`
- `API_BASE_URL=http://127.0.0.1:61001`
- `TOS_BUCKET=autocut-malin`
- `USE_FAKE_TOS=false`
- `ALGORITHM_IMAGE=a-scheduler:0415-af30ae1`

### 4. Worker 已注册到 A 机器 candidate PostgreSQL

已验证数据库中的设备记录：

- `worker_id = worker1-phase6`
- `worker_name = Worker 1 Phase 6`
- `status = IDLE`
- `heartbeat_at` 持续更新

说明：

- 阶段 6 最核心的“Worker 不再留在 A，而是从 Worker 机器接回候选调度中心”已经成立

### 5. 调度任务已经成功分配给 Worker

通过 `phase6_smoke_via_tos` 验证链，已确认：

- A 机器 candidate API 能创建 `smart_cut_tasks`
- analyze 触发后能创建 `scheduler_tasks`
- `scheduler_tasks.assigned_worker_id = worker1-phase6`

示例：

- 业务任务：`8d9d834a-878d-4e0a-b877-c8c47e9e5166`
- 调度任务：`1c16de11-3064-4673-bf54-4f4ab93a90da`
- 状态：`FAILED`
- Worker：`worker1-phase6`

这说明：

- Scheduler -> Worker 分配路径已经打通

## 阻塞点

### 阻塞点 1：candidate API 的 `upload-direct` 走真实 TOS 时返回 403

验证任务：

- `f319eae9-d540-4723-a054-d257f6d637fa`

现象：

- `POST /api/smart-cut/tasks/{task_id}/upload-direct`
- 返回 `500`
- 错误信息为 TOS `403 Forbidden`

这说明：

- 当前 candidate API 使用 `apps/services/tos_service.py` 的真实 TOS 适配层时，`PutObject` 路径不正确

### 阻塞点 2：Worker 下载 TOS 输入时失败

为了绕过 `upload-direct`，阶段 6 用 A 机器上的正式 TOS 工具直传输入文件，再把任务推进到 `READY_ANALYZE`。

这一步验证了：

- 输入对象确实已经写入 `autocut-malin`
- 上传日志显示 `httpCode: 200`

但 Worker 执行 analyze 时仍失败：

- 初始失败：错 bucket，表现为 `HeadObject 404`
- 修复 bucket 入口后：变为 `HeadObject 403`

最终错误：

- `Failed to download smart-cut/.../input/source_video.mp4`
- `An error occurred (403) when calling the HeadObject operation: Forbidden`

这说明：

- Worker 已经开始按正确 bucket 去读
- 但当前真实 TOS 读取仍然被 `apps/services/tos_service.py` 里的真实模式适配层阻塞

## 阶段 6 中的代码调整

### 1. 新增 Worker 候选部署脚本

- `scripts/rebuild_phase6/remote_build_worker_candidate.sh`

职责：

- 在 Worker 机器建立候选部署根
- 使用 `sudo docker` 启动 `worker1-phase6-gateway`
- 指向 A 机器 candidate PostgreSQL 和 API
- 记录 manifest 和 health 文件

### 2. 新增 Worker -> A candidate tunnel 脚本

- `scripts/rebuild_phase6/worker_open_a_candidate_tunnel.sh`

职责：

- 在 Worker 本机建立到 A 机器 candidate 端口的 SSH tunnel

### 3. 新增阶段 6 smoke 脚本

- `scripts/rebuild_phase6/a_machine_phase6_smoke.sh`
- `scripts/rebuild_phase6/a_machine_phase6_smoke_via_tos.sh`

职责：

- 第一条路径：验证 candidate API 标准上传链
- 第二条路径：绕过 candidate API 上传，直接使用正式 TOS 工具上传输入对象，再触发 analyze

### 4. 修复 Worker 侧 bucket 来源

已修改：

- `worker/services/file_transport.py`
- `worker/processors/base_stage_processor.py`

修复内容：

- Worker 不再硬编码 `smart-cut`
- 优先读取环境变量 `TOS_BUCKET`

## 直接证据

### 成功证据

- Worker 设备已注册：
  - `worker1-phase6`
- Worker 心跳持续更新：
  - `heartbeat_at` 持续刷新
- analyze 调度任务已成功创建并分配：
  - `assigned_worker_id = worker1-phase6`

### 失败证据

- `upload-direct` -> `403 Forbidden`
- `phase6_smoke_via_tos` 输入上传成功，但 analyze 仍失败
- 最终任务状态：
  - `ANALYZE_FAILED`
- 最终 scheduler task 状态：
  - `FAILED`

## 对下一步的直接指令

下一步不要再继续折腾 Worker 连接和任务分配，它们已经成立。

下一步应只处理一件事：

- 修复 `apps/services/tos_service.py` 在真实 TOS 模式下的读写实现

优先级建议：

1. 先在 candidate API / Worker 所用环境里做最小 TOS 读写实验
2. 判定是：
   - `boto3` 适配方式错误
   - 还是必须切到火山官方 `tos` SDK
3. 修通 `upload-direct`
4. 修通 Worker 的 `download_file`
5. 重新跑 `phase6_smoke_via_tos`

在这一步完成前，不要进入阶段 7。
