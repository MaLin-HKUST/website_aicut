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

当前仓库代码仍然是旧模型：

- `smart_cut_tasks` 仍然是隐藏草稿语义
- `draft/current` / `draft/current/ensure` 仍然存在
- `visible_in_task_center` 仍然是“隐藏/显示”的关键字段
- `session_scope_id` 仍然参与草稿恢复
- `task_center` 普通用户列表仍按 `user_id` 查
- Smart Cut 主模型里还没有 `company_id`
- 也还没有 `smart_cut_task_runs` 这张子执行表

所以这个专项包不是“记录已完成重构”，而是：

- 明确当前真实现状
- 定义目标模型
- 把差距拆成最小可执行任务

## 阅读顺序

1. `06_上线前备份与下线动作.md`
2. `01_当前代码真实状态审计.md`
3. `02_产品模型与状态机.md`
4. `03_数据模型与表结构.md`
5. `04_API契约与状态推进.md`
6. `05_前端工作台与任务列表重构.md`
7. `07_迁移、上线与E2E验收.md`
8. `08_旧版本问题清单与退役边界.md`
9. `task.json`
10. `progress.md`

## 目录结构

- `01_当前代码真实状态审计.md`
- `02_产品模型与状态机.md`
- `03_数据模型与表结构.md`
- `04_API契约与状态推进.md`
- `05_前端工作台与任务列表重构.md`
- `06_上线前备份与下线动作.md`
- `07_迁移、上线与E2E验收.md`
- `08_旧版本问题清单与退役边界.md`
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
