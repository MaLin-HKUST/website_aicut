# API 契约与状态推进

## 目标

用显式主任务 API 替代当前 `draft/current*` 草稿接口。

## 新 API

## 1. `POST /api/smart-cut/tasks/start`

### 用途

显式开启一个主任务。

### 输入

- `user_id`
- `company_id`
- 可选初始标题或来源信息

### 输出

- `task_id`
- `status = waiting_upload`
- `current_stage = upload`

### 备注

- 进入 `/smart-cut` 不再自动创建任务
- 只有点 `开启任务` 才创建

## 2. `POST /api/smart-cut/tasks/{task_id}/upload-complete`

### 用途

确认视频和文案均已上传。

### 结果

- 创建 `upload run success`
- 主任务推进为 `analyzing`
- 自动创建 `analyze run`
- 自动把 analyze 扔进 scheduler

### 用户体验

- 不再要求用户手动点 `开始分析`

## 3. `POST /api/smart-cut/tasks/{task_id}/preview`

### 用途

基于当前 edit 或 analyze 结果生成试听。

### 输入

- `edited_script`
- 可选 `source_edit_id`

### 结果

- 新增或更新 edit version
- 创建新的 `preview run`
- 成功后主任务回到 `waiting_user`

### 失败语义

- preview 失败不改变主任务为失败态
- 只记在 run 上
- 用户仍然停留在 `waiting_user`
- 允许继续重试

## 4. `POST /api/smart-cut/tasks/{task_id}/finalize`

### 用途

生成最终视频。

### 输入

- 输出规格
- 可选基于哪个 edit version

### 规则

允许两条路径：

1. analyze-only finalize
2. preview-success finalize

### 不再允许的旧限制

- 不再强制要求存在 preview 产物才可 finalize

### 结果

- 创建 `finalize run`
- 主任务进入 `finalizing`
- 当前工作台退出该任务
- 任务列表继续承接状态

## 5. `POST /api/smart-cut/tasks/{task_id}/abandon`

### 用途

显式放弃任务。

### 结果

- 主任务进入 `abandoned`
- 未开始的子执行不再继续
- 页面退出当前任务

## 6. `GET /api/smart-cut/tasks/{task_id}/runs`

### 用途

获取该主任务的 run timeline。

### 用于前端

- 任务详情右侧 timeline
- 失败原因定位
- 历史 preview / finalize 版本追踪

## 7. `GET /api/task-center/tasks`

### 新要求

- 普通用户按 `company_id` 查看主任务
- 返回主任务卡，不返回 preview/finalize 子执行卡

## 退役接口

以下接口应在新模型上线后退役：

- `GET /api/smart-cut/tasks/draft/current`
- `POST /api/smart-cut/tasks/draft/current/ensure`
- `POST /api/smart-cut/tasks/draft/current/abandon-all`

## 状态推进规则

### 主任务

- `waiting_upload -> uploading -> analyzing -> waiting_user -> finalizing -> success`
- 任意时刻可：
  - `-> abandoned`

### 子执行

- `created -> queued -> running -> success`
- `created -> queued -> running -> failed`

### 失败回退

- analyze 失败：
  - 主任务仍回到可恢复/可重试状态
  - 由产品决定是回 `waiting_upload` 还是 `waiting_user`
  - 当前建议：回 `waiting_upload` 并保留错误提示
- preview 失败：
  - 主任务回 `waiting_user`
- finalize 失败：
  - 主任务回 `waiting_user`

## 单一真相要求

### API 真相

- `smart_cut_tasks` 是主任务真相
- `smart_cut_task_runs` 是执行真相
- `scheduler_tasks` 是底层派单真相

### 不允许

- 页面本地缓存自行制造“当前任务”
- 只有 Smart Cut API 认识、scheduler 不认识的假 task
- 前端进度条显示上传/分析中，但 PG 没有对应主任务/run 的状态
