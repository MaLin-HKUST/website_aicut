# Smart Cut Task Card Refactor Progress

## 当前阶段

- `L00` 已完成：
  - live Smart Cut 前端备份
  - 旧入口下线
  - 旧前端实现 quarantine
- `L01` 正在完成：
  - 当前代码真实状态审计
  - 旧方案废止边界
  - 新执行包结构重写
  - 旧分支历史切割
- `L02` 已启动：
  - 主任务字段增量补齐
  - `smart_cut_task_runs` 新表落地
- `L03` 已完成：
  - 显式 `start task`
  - upload 完成后自动 analyze
  - preview retry
  - analyze-only finalize
  - `runs` 查询接口
- `L04` 已完成：
  - 主任务 / run / scheduler_task 映射
  - ghost task 自动回收
  - task center 优先按 `company_id` 过滤
- `L05` 已完成：
  - `/smart-cut` 空态与开启任务
  - 新工作台
  - 任务列表继续处理入口
  - 本地草稿缓存退出主路径

## 这次修正后的结论

### 1. `70_*` 现在升级为唯一执行主包

- `50_*` 降级为历史参考
- 后续实现、验收、回滚文档都优先回写 `70_*`

### 2. 当前仓库仍然是旧隐藏草稿模型

已经写入审计文档的关键事实：

- `apps/models/task.py` 仍然使用 `visible_in_task_center`
- `apps/models/task.py` 仍然有 `session_scope_id`
- `apps/api/routes/tasks.py` 仍然有 `draft/current*`
- `apps/api/routes/task_center.py` 普通用户列表仍按 `user_id`
- Smart Cut 后端主模型里还没有 `company_id`
- 当前没有 `smart_cut_task_runs`

### 3. 之前 codebook 的主要缺口已补方向

此前缺口：
- 只有 L00，没有可执行设计正文
- 没有拆到每个大任务的独立目录
- 没有说明 50_* 与 70_* 的关系
- 没有把当前真实代码现状写清楚

当前已补：
- 01~07 设计文档骨架与正文
- `08_旧版本问题清单与退役边界.md`
- `tasks/L00~L07` 子目录
- 每个大任务独立 `task.json/progress.md/progress.json`
- `git/branch_strategy.md`

### 4. 旧分支污染已经开始收口

- 当前执行分支已切到：
  - `feature/smart-cut-taskcard-refactor`
- 旧分支：
  - `feature/smart-cut-workspace-refactor-R10-R11-integration`
  只保留为 `L00` 的历史来源

## 已完成任务

- 建立专项包 `70_smart_cut_task_card_refactor_2026-04-23`
- 写入备份与下线记录 `06_上线前备份与下线动作.md`
- 把旧 Smart Cut 前端入口切成维护页
- 把旧前端实现移入 quarantine
- 把 `70_*` 从 L00 骨架升级成完整执行包
- 补录当前代码审计和真实差距
- 新建每个大任务的独立任务目录
- 新增 `08_旧版本问题清单与退役边界.md`
- 切出新的专项执行分支 `feature/smart-cut-taskcard-refactor`
- 新增 `apps/models/task_run.py`
- 给 `smart_cut_tasks` 增量补齐：
  - `company_id`
  - `current_run_id`
  - `latest_successful_run_id`
  - `failed_stage`
  - `abandoned_at`
  - `revision_count`
- 新增后端接口：
  - `POST /api/smart-cut/tasks/start`
  - `GET /api/smart-cut/tasks/{task_id}/runs`
- 任务中心普通用户列表新增 `company_id` 优先过滤
- 上传直达和 `upload-complete` 现在会自动创建 analyze run + scheduler task
- preview 失败和 finalize 失败现在会回到 `waiting_user`
- finalize 现在允许 analyze-only（无 pause cuts 时走空配置）
- scheduler 现在会同步更新 task_run，并回收 orphaned business tasks
- `/smart-cut` 已替换为显式任务卡工作台
- `/smart-cut/[taskId]` 可继续处理指定主任务
- 任务列表已可跳回 `/smart-cut/{taskId}`
- 新增最小验证：
  - `tests/test_task_card_schema.py`
  - `tests/test_task_truth_reconcile.py`
- live fresh 短样本链路：
  - `start`
  - `upload-prepare`
  - 直传 TOS
  - `upload-complete`
  - 自动 `analyze`
  - analyze-only `finalize`
  已跑通并产出最终视频

## 进行中

- `L01/S106`
  - 把审计结果继续压缩成后续实现前提
- 准备进入：
  - `L02` 主任务模型与数据库设计

## 决策记录

- 新模型的唯一主入口是显式 `开启任务`
- `preview` 是可选循环，不再是 `finalize` 的硬前置
- `退出登录` 不自动放弃任务
- 真正终止主任务只能通过显式 `放弃任务`
- 任务列表只展示主任务卡，不平铺 preview/finalize 子执行
- 子执行历史通过 timeline 展示
- `50_*` 只保留历史参考价值，不再作为实现依据

## 提交历史

- `fcb3e11`
  - 目的：在任务卡重构开始前关闭 live Smart Cut 前端入口
  - 影响：维护页替换 `/smart-cut`，左侧导航禁用，任务列表不再跳回旧 Smart Cut 页面
  - 验证：
    - `apps/web` TypeScript 编译通过
    - `apps/web` Next.js 生产构建通过
    - `https://xiaomajianji.cn/smart-cut` 返回维护页
    - `https://xiaomajianji.cn/smart-cut/<taskId>` 返回维护页

## 文件修改历史

- `01_当前代码真实状态审计.md`
  - 补录当前仓库仍然是隐藏草稿模型
- `02_产品模型与状态机.md`
  - 定义显式主任务卡 + 子执行记录模型
- `03_数据模型与表结构.md`
  - 定义 `smart_cut_task_runs` 和主任务字段重构方向
- `04_API契约与状态推进.md`
  - 定义 `start task / abandon / analyze-only finalize / runs timeline`
- `05_前端工作台与任务列表重构.md`
  - 定义空态、开启任务、任务卡、timeline 和放弃任务
- `07_迁移、上线与E2E验收.md`
  - 定义迁移顺序和真实 E2E
- `08_旧版本问题清单与退役边界.md`
  - 定义旧版本问题列表和退役边界
- `tasks/L00~L07/*`
  - 新增每个大任务的独立 task/progress 文件
- `apps/models/task.py`
  - 增量补齐主任务卡所需字段
- `apps/models/task_run.py`
  - 新增子执行记录模型
- `configs/database.py`
  - 新增增量补列与 `task_runs` 建表初始化
- `apps/api/models/schemas.py`
  - 新增 `TaskStartRequest/Response` 和 `TaskRunRead`
- `apps/api/routes/tasks.py`
  - 新增显式 `start task` 与 `runs` 查询接口
- `apps/api/routes/task_center.py`
  - 新增 `company_id` 优先过滤
- `apps/api/routes/upload.py`
  - 上传后自动触发 analyze 并创建 run/scheduler task
- `apps/api/routes/stages.py`
  - preview retry、analyze-only finalize、run 创建
- `apps/scheduler/scheduler_service.py`
  - run 状态同步和 orphaned task 回收
- `apps/web/lib/task-center.ts`
  - 前端 task-center 查询支持 `companyId`
- `apps/web/lib/smart-cut.ts`
  - 新任务卡前端 API 客户端
- `apps/web/components/smart-cut/script-editor.tsx`
  - 删除线编辑器恢复到新工作台
- `apps/web/components/smart-cut/workspace.tsx`
  - 新显式任务卡工作台
- `apps/web/app/smart-cut/page.tsx`
  - 新工作台入口
- `apps/web/app/smart-cut/[taskId]/page.tsx`
  - 继续处理指定任务入口
- `apps/web/components/navigation/user-workspace-shell.tsx`
  - 重新开放 smart-cut 导航入口
- `apps/web/components/navigation/use-user-workspace-data.ts`
  - workspace 数据改用 company 维度
- `apps/web/components/task-center/task-center-shell.tsx`
  - smart_cut 任务增加“继续处理”入口
- `tests/test_task_card_schema.py`
  - 验证新表和新增字段
- `tests/test_rel0415_api.py`
  - 回归 `start task` / `runs` / company filter
- `tests/test_smart_cut_preview_validation.py`
  - 锁住 `preview_failed` 可重试
- `tests/test_task_truth_reconcile.py`
  - 锁住 ghost task 回收
- `worker/services/algorithm_runner.py`
  - 强制算法子容器走 `--entrypoint python`
- `worker/processors/finalize_processor.py`
  - analyze-only finalize 的空 pause cuts 改成结构化对象
- `scripts/rebuild_phase6/remote_build_worker_candidate.sh`
  - worker gateway 重建时显式传入 `BYTEDANCE_ASR_APPID/TOKEN`

## 已知风险

- 这一步完成的是 **可执行设计包**，不是重构代码本身
- 当前仓库仍同时保留旧 draft 接口，虽然前端已经不再走它们
- 这次还没有重新部署 live runtime/API/worker
- `L06-L07` 已部分完成：analyze-only live E2E 已通；preview-loop / 继续编辑 / 放弃任务 尚未重新做一轮 live fresh 验证
- `L00` 的历史提交仍来自旧分支，但后续实现已经切到 `feature/smart-cut-taskcard-refactor`

## Live 证据

- 成功任务：
  - `2ca436b1-3fbf-4d67-9c6e-d1ee1e41d736`
- 最终状态：
  - `success / complete`
- 下载对象：
  - `smart-cut/2ca436b1-3fbf-4d67-9c6e-d1ee1e41d736/finalize/final_video.mp4`
- 对象检查：
  - `HEAD 200`
  - `Content-Length: 2706475`

## 本轮新增根因记录

1. A 机 API `.venv313` 缺 `tos` 及其依赖，导致真实 TOS 模式无法稳定工作。
2. worker gateway 初次重建时未传 ASR 凭证，导致 analyze 子容器 `run_raw_cut.py --flow-a` 失败。
3. analyze-only finalize 的空 `pause_cuts` 结构错误，算法期望对象而不是列表。
