# 粗剪 Smart Cut 调度实施计划

## 1. 文档目标

本文档用于定义“智能剪口播气口（Smart Cut）”接入任务调度系统的详细实施方案。

目标不是停留在“可手工进容器运行脚本”，而是将现有三阶段处理链路升级为：

- 可被 scheduler 派工
- 可由真实 `smart_cut_worker` 执行
- 可通过 TOS 进行跨步骤、跨 Worker 的输入输出流转
- 可通过 Harness 进行自动化、Fake TOS、真实 TOS 三层验证
- 可使用真实数据完成上线前阻断验收

本计划对应的 Harness 根目录固定为：

```text
/Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/cujian_scheduler
```

本计划的真实数据验收标准固定引用以下两份文档：

- `/Users/malin13/Documents/trae_projects/website_aicut/doc/cujiian/粗剪的调度的测试/真实数据上线验收测试用例清单.md`
- `/Users/malin13/Documents/trae_projects/website_aicut/doc/cujiian/粗剪的调度的测试/真实数据上线验收执行记录表.md`

---

## 2. 当前状态与问题

当前仓库已有：

- Smart Cut 处理链路规格：`cujian_plan_cx2.md`
- 第一层容器测试 worker：`worker/README.md` 对应的 `smart_cut_worker`
- 在线版处理器实现位于 `aicut2602/.../online_version`
- 第一层后端联调脚本位于 `tests/test_cujiian`

当前能力不足点：

1. 现有 worker 仍然是“手工执行容器”，不是会自行拉任务的真实 Worker
2. Smart Cut 还没有被建模成“业务任务 + 调度任务”两层
3. 目前没有把 `analyze / preview / finalize` 作为独立调度阶段接入 scheduler
4. 没有为多次 preview、换 Worker 接续、失败状态拆分建立完整数据模型
5. 没有一套独立 Harness 来跟踪该专项的 backlog、环境、真实数据验收和清理

---

## 3. 实施目标

本次改造完成后，系统必须满足以下目标：

1. Smart Cut 成为一个可调度业务能力
2. `smart_cut_analyze`、`smart_cut_preview`、`smart_cut_finalize` 成为三种独立调度任务
3. 用户上传大文件采用“前端直传 TOS + upload-complete 绑定”的模式
4. Worker 从 TOS 下载输入，执行后将结果再回传 TOS
5. 每一个阶段完成后都释放 Worker，不阻塞等待用户
6. preview 可执行多次，finalize 只能读取最后一次成功 preview 的产物
7. 后续阶段允许换 Worker 接续
8. Fake TOS 能用于高频集成回归，真实 TOS 能用于最终上线验收
9. 测试结束后，Fake TOS 与 worker 本地缓存都能被清空

---

## 4. 设计总原则

### 4.1 业务任务与调度任务分层

对外是一个 `smart_cut` 业务任务；对内是三个阶段调度任务：

- `smart_cut_analyze`
- `smart_cut_preview`
- `smart_cut_finalize`

业务任务负责：

- 用户视角状态
- 输入文件绑定
- 当前阶段
- preview 历史与活跃 edit
- 最终结果 URL/key

调度任务负责：

- 具体阶段派工
- Worker 分配
- 设备状态推进
- 失败/重试/报警

### 4.2 前端直传 TOS

大文件不经过 API 服务体传输。

固定链路为：

1. 创建任务
2. `upload-prepare`
3. 浏览器直传 TOS
4. `upload-complete`
5. 后端校验 key 与对象存在性
6. 通过后才允许进入 analyze

### 4.3 跨步骤必需产物必须持久化

不能依赖容器本地目录作为唯一真相。

必须持久化的对象：

- 输入视频
- 参考文案
- analyze 的 script
- analyze 的 asr_result
- preview 的 edited_delay_cuts
- preview 的 pause_cuts_on_original
- preview 的 audio_b
- finalize 的 final_video
- finalize 产生的 GroundTruth 目录

### 4.4 每一步完成后释放 Worker

- analyze 成功后，任务进入 `waiting_user`
- preview 成功后，任务回到 `waiting_user`
- finalize 成功后，任务进入 `success`

Worker 在每一步结束后回到空闲。

### 4.5 后续步骤允许换 Worker

只要新 Worker 能力兼容，并且必需输入在 TOS/数据库中可获得，后续阶段可以由任意兼容 Worker 接续。

---

## 5. 目标部署与运行时约束

### 5.1 真实 Worker 镜像

本专项的真实 worker 镜像路径固定为：

```text
/Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz
```

该镜像作为执行底座使用，不在本计划中重新定义镜像构建策略。

### 5.2 Fake TOS 位置

Fake TOS 固定使用宿主机外挂盘目录：

```text
/Volumes/XIAOMA-A-1T/docker_hub/FakeTos
```

设计理由：

- 空间够大，可放真实视频与中间产物
- 不依赖容器生命周期
- 便于取证和统一清理
- 便于 API、测试脚本、worker 容器共享

容器内挂载路径建议固定为：

```text
/fake-tos
```

### 5.3 清理原则

每次测试必须执行两段清理：

1. 测试开始前清理本次 `run_id`
2. 测试结束后清理：
   - `/Volumes/XIAOMA-A-1T/docker_hub/FakeTos/{run_id}`
   - `/data/smart-cut/{task_id}`
   - 本次 Harness 标记为临时的产出

不得依赖人工记忆清理。

---

## 6. 数据模型详细方案

### 6.1 业务任务表 `smart_cut_tasks`

新增或补齐以下字段：

- `id`
- `user_id`
- `status`
- `current_stage`
- `original_video_url`
- `original_video_tos_key`
- `reference_text_url`
- `reference_text_tos_key`
- `analyze_script`
- `analyze_script_tos_key`
- `asr_result_tos_key`
- `active_edit_id`
- `finalize_source_edit_id`
- `final_video_url`
- `final_video_tos_key`
- `groundtruth_url`
- `groundtruth_tos_key`
- `feed_to_ai`
- `last_scheduler_task_id`
- `error_stage`
- `error_message`
- `created_at`
- `updated_at`

### 6.2 Preview 历史表 `smart_cut_edits`

新增表保存每次 preview：

- `id`
- `task_id`
- `edited_script`
- `status`
- `audio_b_url`
- `audio_b_tos_key`
- `edited_delay_cuts_tos_key`
- `pause_cuts_on_original_tos_key`
- `created_at`
- `updated_at`

### 6.3 调度任务 payload

scheduler task 需要承载阶段输入信息，按 `task_type` 区分：

#### analyze payload
- `smart_cut_task_id`
- `original_video_tos_key`
- `reference_text_tos_key`

#### preview payload
- `smart_cut_task_id`
- `edit_id`
- `edited_script`
- `original_video_tos_key`
- `asr_result_tos_key`

#### finalize payload
- `smart_cut_task_id`
- `edit_id`
- `original_video_tos_key`
- `edited_delay_cuts_tos_key`
- `pause_cuts_on_original_tos_key`
- `output_mode`
- `feed_to_ai`

---

## 7. 状态机详细方案

### 7.1 业务任务状态

固定状态：

- `created`
- `waiting_upload`
- `ready_analyze`
- `analyzing`
- `waiting_user`
- `previewing`
- `ready_finalize`
- `finalizing`
- `success`
- `failed`

### 7.2 失败阶段

失败不只用一个 `failed`，必须记录具体阶段：

- `input_upload_failed`
- `analyze_failed`
- `preview_failed`
- `preview_upload_failed`
- `finalize_failed`
- `final_upload_failed`
- `groundtruth_upload_failed`

### 7.3 状态推进规则

#### 创建后
- `created -> waiting_upload`

#### 输入绑定后
- `waiting_upload -> ready_analyze`

#### analyze 派工
- `ready_analyze -> analyzing`

#### analyze 成功
- `analyzing -> waiting_user`

#### preview 派工
- `waiting_user -> previewing`

#### preview 成功
- `previewing -> waiting_user`

#### finalize 派工
- `waiting_user -> finalizing`

#### finalize 成功
- `finalizing -> success`

---

## 8. API 详细方案

### 8.1 `POST /api/smart-cut/tasks`

职责：

- 创建业务任务
- 返回 `task_id`
- 初始状态为 `waiting_upload`

### 8.2 `POST /api/smart-cut/tasks/{id}/upload-prepare`

职责：

- 为当前任务分配输入文件目标 key
- 返回视频与文案的上传参数

固定目标 key：

- `smart-cut/{task_id}/input/source_video.{ext}`
- `smart-cut/{task_id}/input/reference.txt`

### 8.3 `POST /api/smart-cut/tasks/{id}/upload-complete`

职责：

- 校验前缀属于当前任务
- 校验 prepare 与 complete 对应
- 校验对象真实存在
- 通过后把任务推进到 `ready_analyze`

### 8.4 `POST /api/smart-cut/tasks/{id}/analyze`

职责：

- 仅创建 `smart_cut_analyze` 调度任务
- 不在请求线程直接跑算法
- 推进业务状态到 `analyzing`

### 8.5 `POST /api/smart-cut/tasks/{id}/preview`

职责：

- 校验 `edited_script`
- 创建新的 preview 记录 `edit_id`
- 创建 `smart_cut_preview` 调度任务
- 推进业务状态到 `previewing`

### 8.6 `POST /api/smart-cut/tasks/{id}/finalize`

职责：

- 读取最后一次成功 preview
- 显式传入：
  - `output_mode`
  - `feed_to_ai`
- 创建 `smart_cut_finalize` 调度任务

### 8.7 `GET /api/smart-cut/tasks/{id}`

职责：

- 返回任务详情
- 在 `success` 状态时必须至少返回：
  - `final_video_url`
  - `download_text`
  - `groundtruth_saved`

---

## 9. Worker 运行时详细方案

### 9.1 Worker 职责

worker runtime 需要完成：

- 注册自身与能力集
- 上报 heartbeat
- 拉取已分配给自己的 scheduler task
- 按 `task_type` 执行阶段处理
- 回写设备状态
- 回写阶段结果

### 9.2 Worker 能力集

默认能力：

- `smart_cut_analyze`
- `smart_cut_preview`
- `smart_cut_finalize`

### 9.3 阶段处理

#### analyze
- 从 TOS 下载：
  - 原视频
  - 参考文案
- 调用 `analyze_processor`
- 上传/回写：
  - `script`
  - `asr_result`
- 业务任务推进为 `waiting_user`

#### preview
- 读取当前 edit 的 `edited_script`
- 从 TOS 下载：
  - 原视频
  - asr_result
- 调用 `preview_processor`
- 上传/回写：
  - `audio_b`
  - `edited_delay_cuts`
  - `pause_cuts_on_original`
- 更新 `active_edit_id`
- 业务任务回到 `waiting_user`

#### finalize
- 读取 `active_edit_id`
- 从 TOS 下载：
  - 原视频
  - `edited_delay_cuts`
  - `pause_cuts_on_original`
- 调用 `finalize_processor`
- 上传：
  - `final_video`
  - 可选 `GroundTruth`
- 业务任务推进到 `success`

### 9.4 容器工作目录

固定：

```text
/data/smart-cut/{task_id}/
├── input/
├── analyze/
├── preview/{edit_id}/
└── final/
```

---

## 10. 对象存储详细方案

### 10.1 真实 TOS

真实数据验收必须使用真实 TOS。

### 10.2 Fake TOS

Fake TOS 只用于集成层回归，不作为最终上线验收环境。

Fake TOS 对象路径固定使用 run_id：

```text
smart-cut-e2e/{run_id}/{task_id}/...
```

### 10.3 必须持久化的对象

#### 输入
- 原视频
- 参考文案

#### analyze
- script
- asr_result

#### preview
- audio_b
- edited_delay_cuts
- pause_cuts_on_original

#### finalize
- final_video
- GroundTruth 目录

---

## 11. 实施分期

### Phase 1：模型与上传绑定
- 建 `smart_cut_tasks`
- 建 `smart_cut_edits`
- 补 `upload-prepare`
- 补 `upload-complete`

### Phase 2：Analyze 调度接入
- 业务任务触发 analyze
- analyze 调度任务派工
- analyze 成功后进入 `waiting_user`

### Phase 3：Preview 调度接入
- 建 preview edit 历史
- preview 多次执行
- 活跃 edit 收敛

### Phase 4：Finalize 与结果上传
- finalize 读取最后一次成功 preview
- 上传 final_video
- 处理 GroundTruth
- 失败阶段拆分

### Phase 5：Harness 与验收
- 建 `HarnessPlan/cujian_scheduler`
- 建 Fake TOS 机制
- 建真实数据验收流程
- 形成可上线判断

---

## 12. Harness 设计方案

### 12.1 Harness 根目录

```text
/Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/cujian_scheduler
```

### 12.2 标准 artifact

- `app_spec.txt`
- `feature_list.json`
- `claude-progress.txt`
- `init.sh`
- `README.md`
- `case_catalog.yaml`
- `reports/RESULT_TEMPLATE.md`
- `run_release_gate.py`

### 12.3 附加目录

- `configs/`
- `scripts/`
- `cases/auto/`
- `cases/fake_tos/`
- `cases/real_tos/`

### 12.4 Harness backlog

固定为：

- F01 Harness Bootstrap And Spec Lock
- F02 Smart Cut Scheduler Data Model
- F03 Upload Prepare/Complete And TOS Binding
- F04 Analyze Stage Scheduling
- F05 Preview Stage Scheduling And Edit History
- F06 Finalize Stage Scheduling And Result Upload
- F07 Worker Runtime And Heartbeat Loop
- F08 Fake TOS Integration Layer
- F09 Automated Regression Coverage
- F10 Real-Data Release Gate And Cleanup

---

## 13. 测试实施方案

### 13.1 自动化规则层

目的：

- 验证调度逻辑
- 验证业务状态推进
- 验证重复点击、非法输入、阶段唯一性

### 13.2 Fake TOS 集成层

目的：

- 在不依赖真实云对象存储的情况下验证“对象存储交互逻辑”
- 验证 key、上传下载、回写、清理

注意：

- Fake TOS 不是最终上线环境
- Fake TOS 是高频回归环境

### 13.3 真实数据上线验收层

唯一验收清单为：

- `真实数据上线验收测试用例清单.md`

执行记录必须落到：

- `真实数据上线验收执行记录表.md`

---

## 14. 上线判定

只有以下全部成立，才允许上线：

1. 自动化测试通过
2. Fake TOS 集成测试通过
3. 真实数据验收中全部 P0 通过
4. 真实数据验收中全部 P1 通过
5. 执行记录表完整
6. Fake TOS 与 worker 本地缓存 cleanup 通过

如果任一 P0 或 P1 失败，则禁止上线。
