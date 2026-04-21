# Agent 02 任务书：R03 任务中心可见性

## 你的角色

你专门负责任务中心语义收口。

你只负责：

- `R03` 任务中心可见性改造

你不负责：

- 会话草稿接口设计
- `/smart-cut` 页面入口
- analyze/preview/finalize 页面交互

## 开始时机

你必须在 Agent 01 的契约被主集成人接受后再开始。

也就是说，只有当这两个问题已经定稿后，你才能动手：

- `visible_in_task_center`
- `session_scope_id`

## 必读上下文

1. [../README.md](../README.md)
2. [../04_任务中心可见性规则.md](../04_任务中心可见性规则.md)
3. [../task.json](../task.json)
4. [01_agent_R01_R02_数据与接口契约.md](./01_agent_R01_R02_数据与接口契约.md)
5. 仓库根 `AGENTS.md`

## 你要改哪些文件

优先写入范围：

- `apps/api/routes/tasks.py`
- `apps/api/routes/task_center.py`
- 相关 query/service 文件
- 如需要，补一条历史数据回填脚本或 migration backfill

不要改：

- `apps/web/components/smart-cut/*`
- `apps/web/app/smart-cut/*`
- Worker 逻辑

## 你要完成什么

1. task-center 查询只返回 `visible_in_task_center = true`
2. 历史空任务和中间态草稿从任务中心隐藏
3. 已完成任务仍保持可见
4. 明确 finalize 之后的任务标题与时间展示是否正确映射到任务中心

## 起点

当前问题：

- `waiting_upload`
- `ready_analyze`
- `analyzing`

这些中间态任务会污染任务列表。

## 终点

主集成人接手时应能直接验证：

- 进入 `/smart-cut` 或上传阶段不再产生任务中心空卡
- finalize 后才会在任务列表中看到正式任务
- 历史已完成任务仍然保留

## 你需要的验证

至少提供：

- 接口响应前后对比
- 一条历史中间态任务被隐藏的证据
- 一条已完成任务仍可见的证据

推荐验证：

- 针对 `task-center` 的 pytest
- 相关 SQL / DB snapshot 摘要

## 你回交时必须给我什么

严格按 [99_交付回交模板.md](./99_交付回交模板.md) 回交。

并补充：

- 哪些状态被隐藏
- 哪些状态保留可见
- 历史数据是怎么处理的

## Git 要求

- 建议分支名：
  - `feature/smart-cut-workspace-refactor-R03-task-center-visibility`
- 必须给出：
  - `branch`
  - `commit SHA`

## 阻塞规则

如果你发现：

- Agent 01 的契约还没稳定
- 你的实现必须修改 `/smart-cut` 页面逻辑才能成立

你要停止并把阻塞写回来，不要越权改前端页面。
