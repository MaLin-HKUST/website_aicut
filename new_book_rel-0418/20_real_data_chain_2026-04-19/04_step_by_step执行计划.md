# 04_step_by_step执行计划

本文回答什么问题：

- 本专项实际应该按什么步骤推进
- 每一步需要什么输入
- 每一步做完之后要怎么验证
- 哪些失败可以重试，哪些失败必须停下修代码

## 执行原则

1. 先文档，再执行
2. 先只读核查，再真正跑任务
3. 先拿到真实闭环证据，再进入热补收口
4. 每一步都要留下 artifacts

## Step 0：确认前置状态

### 输入

- `../基础网络信息和账号信息.md`
- `../10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md`
- `../10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md`

### 需要做什么

- 确认 A 机器仍然跑着：
  - web on `127.0.0.1:3301`
  - legacy API on `127.0.0.1:8000`
  - candidate API on `18001`
  - candidate PostgreSQL on `55433`
  - candidate Scheduler
- 确认 Worker 仍然跑着：
  - `worker1-phase6-gateway`
- 确认正式域名仍代理到 `127.0.0.1:3301`

### 网络操作

- SSH A 机器
- SSH Worker 机器
- `curl` 正式域名

### 达成效果

- 确认执行环境没有在本专项开始前再次漂移

### 验证

- A 机器容器和端口状态与 `11` 文档一致
- Worker 容器状态与 `11` 文档一致
- 域名页面标记仍正确

## Step 1：确认真实样本可读

### 输入

- `/Volumes/XIAOMA-A-1T/wei_videodb/C2384_reencoded.mp4`
- `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`

### 需要做什么

- 确认可读
- 记录文件大小
- 记录视频基础元信息

### 网络操作

- 无远端写操作

### 达成效果

- 本轮真实样本输入已固定，不再变化

### 验证

- `test -r` 通过
- `ffprobe` 能读出基础信息
- `wc -c` 能读出文案长度

## Step 2：建立本轮 artifacts 目录

### 输入

- 本专项目录

### 需要做什么

- 创建本轮专用 artifacts 目录，例如：
  - `artifacts/<timestamp>_real_data_run/`
- 预留文件：
  - `create.json`
  - `upload.json`
  - `analyze_complete.json`
  - `preview_complete.json`
  - `final_success.json`
  - `worker_logs.txt`
  - `tos_objects.txt`
  - `summary.md`

### 网络操作

- 无

### 达成效果

- 后续执行的证据有固定落点

### 验证

- 目录存在
- 证据文件命名规范已固定

## Step 3：创建真实数据业务任务

### 输入

- 当前正式 API 入口

### 需要做什么

- 调用：
  - `POST /api/smart-cut/tasks`
- 创建新的业务任务
- 记录任务 ID

### 网络操作

- 调用 A 机器当前正式 API

### 达成效果

- 获得一个本轮新的业务任务 ID

### 验证

- `create.json` 返回成功
- `task_id` 不等于 phase 7 的旧任务 ID

## Step 4：上传真实样本

### 输入

- 本轮业务任务 ID
- `C2384_reencoded.mp4`
- `ref.txt`

### 需要做什么

默认主路径：

- 调用：
  - `POST /api/smart-cut/tasks/{task_id}/upload-direct`
- 直接上传真实视频和真实文案

fallback 路径：

- 如果 `upload-direct` 因请求体、代理、上传路径失败，则改走：
  - `upload-prepare`
  - 使用正式 TOS 上传工具链直传对象
  - `upload-complete`

### 网络操作

- 本机到 A 机器 API
- 必要时本机到 TOS

### 达成效果

- 任务进入 `ready_analyze`

### 验证

- `upload.json` 成功
- 任务详情显示 `ready_analyze`
- TOS 中存在输入对象

## Step 5：运行 analyze

### 输入

- 任务 ID

### 需要做什么

- 调用：
  - `POST /api/smart-cut/tasks/{task_id}/analyze`
- 轮询任务详情

### 网络操作

- A 机器 API
- Worker 消费调度任务
- Worker 与 TOS 交互

### 达成效果

- 任务进入：
  - `status = waiting_user`
  - `current_stage = user_select`

### 验证

- `analyze_complete.json` 存在
- TOS 中存在：
  - `asr.json`
  - `script.json`
  - `delay_cuts.json`
  - `audio_a.mp3`
- Worker 日志中出现本轮 analyze 任务

## Step 6：运行 preview

### 输入

- analyze 完成后的脚本内容
- 任务 ID

### 需要做什么

- 从任务详情中取：
  - `current_edited_script` 或 `analyze_script`
- 调用：
  - `POST /api/smart-cut/tasks/{task_id}/preview`

### 网络操作

- A 机器 API
- Worker 消费 preview 任务
- Worker 与 TOS 交互

### 达成效果

- 任务重新进入：
  - `status = waiting_user`
  - `current_stage = user_select`

### 验证

- `preview_complete.json` 存在
- 出现新的 `active_edit_id`
- TOS 中存在 preview 音频
- Worker 日志中出现本轮 preview 任务

## Step 7：运行 finalize

### 输入

- 任务 ID
- `active_edit_id`

### 需要做什么

- 调用：
  - `POST /api/smart-cut/tasks/{task_id}/finalize`
- 使用本轮最新 edit

### 网络操作

- A 机器 API
- Worker 消费 finalize 任务
- Worker 与 TOS 交互

### 达成效果

- 任务进入：
  - `status = success`
  - `current_stage = complete`

### 验证

- `final_success.json` 存在
- `final_video_url` 存在
- TOS 中存在最终视频对象
- Worker 日志中出现本轮 finalize 任务

## Step 8：下载或校验最终结果

### 输入

- `final_video_url`

### 需要做什么

- 优先验证最终对象可访问或可下载
- 至少做：
  - HEAD / 存在性校验
- 如链路允许，做一次真实下载校验

### 网络操作

- A 机器 API / TOS

### 达成效果

- 最终产物不仅“写回了字段”，而且真正存在

### 验证

- `download_check.txt` 或同类证据存在

## Step 9：落档与回写当前状态文档

### 输入

- 本轮任务 ID
- 调度任务 ID
- `active_edit_id`
- TOS key
- Worker 日志摘要

### 需要做什么

- 写本轮真实数据验收报告
- 更新：
  - `11_2026-04-19_当前系统状态.md`
  - `12_2026-04-19_当前Release与证据索引.md`
- 标明：
  - 本轮使用了真实样本
  - 本轮任务 ID 是谁
  - 最终视频对象 key 是谁

### 网络操作

- 无线上改动

### 达成效果

- 当前文档与当前真实链路状态再次对齐

### 验证

- 新报告存在
- `11` 和 `12` 已包含真实数据通过的最新结论

## Step 10：进入热补收口

### 输入

- 本轮真实数据闭环证据

### 需要做什么

- 不是立即改代码，而是根据本轮证据进入下一专项：
  - 热补文件进入标准构建
  - Worker 补齐 `ffprobe`
  - 再用同一真实样本做一轮回归

### 验证

- 热补收口任务已被文档化

## 对 Agent 的直接指令

- 执行顺序不能颠倒。
- 如果真实数据闭环没通过，不要提前做热补收口。
- 如果 `upload-direct` 失败，不要直接宣告链路失败，先走 fallback 上传路径。
