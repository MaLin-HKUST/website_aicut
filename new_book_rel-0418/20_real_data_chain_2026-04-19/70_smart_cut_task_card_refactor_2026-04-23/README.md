# Smart Cut Task Card Refactor

## 定位

这个专项包是当前 **Smart Cut 重构的唯一执行主包**。

- `50_smart_cut_workspace_refactor_2026-04-21/`：
  - 降级为历史参考
  - 只保留“旧隐藏草稿模型是怎么设计和落地的”这类背景信息
  - 不再作为继续实现的依据
- `70_smart_cut_task_card_refactor_2026-04-23/`：
  - 作为后续实现、提测、上线、回滚的唯一主文档集合
  - 所有新增提交、进度、验收证据都应优先回写到这里

## 当前执行分支

- 当前专项执行分支：
  - `feature/smart-cut-taskcard-refactor`
- 旧提交来源分支：
  - `feature/smart-cut-workspace-refactor-R10-R11-integration`
  - 仅保留为 `L00` 下线与备份动作的历史来源
  - 不再承接后续重构提交

## 目标

把 Smart Cut 从“隐藏草稿 + 调度任务双真相”重构成：

- 1 个显式主任务
- 多个子执行记录
- 多个编辑版本
- 1 套以 PostgreSQL 为中心的单一任务真相

并锁定新的产品模型：

- 用户先点 `开启任务`
- 上传完成后自动进入 `analyze`
- `preview` 是可选循环，不是 `finalize` 的硬前置
- 用户可以直接基于 analyze 结果生成视频
- 用户可以显式 `放弃任务`
- 用户可以从任务列表 `继续处理 / 编辑任务`
- 主任务从创建开始就进入任务列表
- 不再依赖隐藏草稿恢复作为主模型

## 当前结论

代码已落地，线上已运行新模型：

- `smart_cut_tasks` 已增量补齐 `company_id`, `current_run_id`, `latest_successful_run_id`, `failed_stage`, `abandoned_at`, `revision_count`
- `smart_cut_task_runs` 新表已创建，记录 upload/analyze/preview/finalize 子执行
- `POST /api/smart-cut/tasks/start` 已上线
- `GET /api/smart-cut/tasks/{task_id}/runs` 已上线
- `/smart-cut` 已替换为显式任务卡工作台
- 任务列表已按 `company_id` 过滤
- analyze-only finalize 已支持

旧模型代码尚未完全清理（技术债务）：

- `draft/current*` 接口代码仍在（计划 L08/S801 清理）
- `visible_in_task_center` 字段仍在（计划 L08/S802 清理）
- `session_scope_id` 字段仍在（计划 L08/S802 清理）

当前工作重心：

- `0425` 上线版冻结与收口
- `L06` 迁移发布准备
- `L07` E2E 全部正式化并记录证据
- `L08` 旧代码清理与文档最终收口

## 阅读顺序

1. `06_上线前备份与下线动作.md`
2. `01_当前代码真实状态审计.md`
3. `02_产品模型与状态机.md`
4. `03_数据模型与表结构.md`
5. `04_API契约与状态推进.md`
6. `05_前端工作台与任务列表重构.md`
7. `10_0425上线版.md`
8. `11_0425上线验收用例.md`
9. `07_迁移、上线与E2E验收.md`
10. `08_旧版本问题清单与退役边界.md`
11. `09_方案B完整收官计划.md`
12. `task.json`
13. `progress.md`

## 目录结构

- `01_当前代码真实状态审计.md`
- `02_产品模型与状态机.md`
- `03_数据模型与表结构.md`
- `04_API契约与状态推进.md`
- `05_前端工作台与任务列表重构.md`
- `06_上线前备份与下线动作.md`
- `07_迁移、上线与E2E验收.md`
- `08_旧版本问题清单与退役边界.md`
- `09_方案B完整收官计划.md`
- `10_0425上线版.md`
- `11_0425上线验收用例.md`
- `task.json`
- `progress.md`
- `progress.json`
- `git/branch_strategy.md`
- `tasks/L00_backup_and_offline/`
- `tasks/L01_current_state_audit/`
- `tasks/L02_task_model_and_schema/`
- `tasks/L03_backend_contracts/`
- `tasks/L04_scheduler_and_truth_unification/`
- `tasks/L05_frontend_workspace_and_task_cards/`
- `tasks/L06_migration_and_release/`
- `tasks/L07_e2e_and_evidence/`
- `tasks/L08_legacy_cleanup/`
- `tasks/L12_scheduler_state_machine_reconcile/`

## 使用规则

- 新的实现计划、接口决策、状态机变更，一律回写到 `70_*`
- 每个大任务都必须维护自己的：
  - `task.json`
  - `progress.md`
  - `progress.json`
- 每个提交都要记录：
  - `sha`
  - `branch`
  - `large_task_id`
  - `small_task_id`
  - `verification`
- 如果 `50_*` 与 `70_*` 冲突，以 `70_*` 为准
