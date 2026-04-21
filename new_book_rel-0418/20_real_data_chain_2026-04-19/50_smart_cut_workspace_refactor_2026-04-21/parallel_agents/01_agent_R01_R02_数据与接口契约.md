# Agent 01 任务书：R01-R02 数据与接口契约

## 你的角色

你负责本专项的契约层。你的输出将决定后续所有 agent 的数据字段、会话草稿语义和接口边界。

你负责：

- `R01` 数据模型方案定稿
- `R02` 会话草稿接口设计

你不负责：

- 前端页面视觉
- 任务中心页面展示
- preview/finalize 页面行为
- 真实浏览器全链路回归

## 开始时机

你可以立即开始。

本任务是并行开发的起点，不需要等待其他 agent。

## 必读上下文

先读这些文件，再开始：

1. [../README.md](../README.md)
2. [../01_目标交互与当前偏差.md](../01_目标交互与当前偏差.md)
3. [../02_数据模型与接口重构.md](../02_数据模型与接口重构.md)
4. [../task.json](../task.json)
5. [../../40_headed_browser_e2e_2026-04-21/README.md](../../40_headed_browser_e2e_2026-04-21/README.md)
6. [../../../README.md](../../../README.md)
7. 仓库根 `AGENTS.md`

必须理解的产品决策：

- Smart Cut 是一个会话草稿的四段生命周期
- 同一登录会话内最多 1 个活动草稿
- logout 后旧草稿失效
- finalize 前任务不进入任务中心

## 你要改哪些文件

优先写入范围：

- `apps/models/task.py`
- 迁移文件
- `apps/api/routes/tasks.py`
- `apps/api/models/schemas.py`
- 如有必要，可增补相关 service 文件

不要改：

- `apps/web/components/smart-cut/*`
- Playwright 页面测试
- Worker 侧 preview/finalize 逻辑

## 你要完成什么

### R01

1. 定义 `visible_in_task_center`
2. 定义 `session_scope_id`
3. 定义历史任务回填策略
4. 明确同一用户同一会话仅 1 个活动草稿的约束落在哪里

### R02

1. 定义 `GET /api/smart-cut/draft/current` 或等价接口
2. 定义 `POST /api/smart-cut/draft/current/ensure` 或等价接口
3. 定义 logout 之后草稿失效规则
4. 定义 finalize 时“可见性切换 + 标题写入 + 调度任务创建”是否必须同事务完成

## 起点

当前系统状态：

- `smart_cut_tasks` 没有这两个字段
- `/smart-cut` 前端仍直接依赖 `create_task`
- 任务中心还会展示中间态任务

## 终点

你交回后，主集成人应该能明确知道：

- 数据结构怎么改
- 迁移怎么写
- 接口怎么长
- 事务边界怎么锁
- 历史数据怎么处理

## 你需要的验证

至少要给出：

- 模型字段定义
- 迁移方案
- API schema/返回体形状
- 若已编码，跑过的最小验证命令

推荐验证命令：

- 相关 pytest
- 相关类型检查
- 如涉及 DB migration，给出 migration dry-run 或 migration 审阅说明

## 你回交时必须给我什么

严格按 [99_交付回交模板.md](./99_交付回交模板.md) 交回。

并且你必须额外写清：

- 你完成的是 `R01`、`R02` 还是两者都完成
- 你的接口命名是否与现有风格完全一致
- 哪些地方你是“方案定稿但未编码”

## Git 要求

- 建议分支名：
  - `feature/smart-cut-workspace-refactor-R01-R02-contract`
- 必须提供：
  - `branch`
  - `commit SHA`
- 必须显式 pathspec 提交，不允许 `git add .`

## 阻塞规则

如果你发现：

- 需要新增第三张业务表
- 需要推翻“单会话 1 草稿”
- 需要改变 finalize 才进入任务中心的产品决策

你不能擅自改。你必须把这个判断写进回交报告，交由主集成人决定。
