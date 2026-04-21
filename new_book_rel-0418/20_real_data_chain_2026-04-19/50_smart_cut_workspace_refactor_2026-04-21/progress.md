# Smart Cut Workspace Refactor Progress

## 当前阶段

- `R01-R02` 已编码并完成最小回归验证
- 专项包已建立
- 其余任务待后续 agent 继续

## 已完成任务

- 建立专项目录
- 写入目标交互、数据模型、前端状态机、任务中心规则、验收标准
- 写入 `task.json`
- 建立 `progress.md` 与 `progress.json`
- 建立并行开发任务书目录 `parallel_agents/`
- 写入 5 个并行 agent 任务书与统一回交模板
- 在 `smart_cut_tasks` 上补入 `task_title / visible_in_task_center / session_scope_id`
- 落地 current draft / ensure draft 接口
- 将 finalize 的标题写入、可见性切换、状态推进、调度任务创建收敛到同一事务提交
- 补充现有数据库的运行时补列与历史可见性回填脚本
- 补充 `tests/test_rel0415_api.py` 回归覆盖

## 正在进行

- 无

## 阻塞项

- 无硬阻塞

## 决策记录

- Smart Cut 按“同一登录会话内 1 个草稿”实现
- 退出登录后旧草稿失效
- finalize 前任务不进入任务中心
- analyze 后页面必须直接展示 `audio_a`
- preview 后页面必须直接展示 `audio_b`
- 并行开发按 5 个 agent 分工执行
- Agent 01 先行锁定契约，其余 agent 按依赖关系启动

## 需要同步给其他 Agent 的上下文

- 这不是局部前端修补，而是交互生命周期重构
- 不要再沿用“点击 `/smart-cut` 立即 create_task” 的旧语义
- 不要让 task-center 继续显示 `waiting_upload` 等中间态

## 最近一次验证结果

- `pytest tests/test_rel0415_api.py`
- current draft / ensure draft 已验证同会话复用、跨会话隔离、缺失会话时报错
- finalize 已验证同次提交内写入标题并切换 `visible_in_task_center=true`

## 已知问题记录

### ISSUE-001
- 标题：当前 `/smart-cut` 入口自动创建空任务
- 位置：`apps/web/components/smart-cut/workspace.tsx`
- 症状：点击左侧“智能剪气口”会在任务中心生成 `waiting_upload`
- 当前判断：当前实现与产品交互不一致，必须整体改入口语义
- 下一步：在 `R04` 中删除 landing 自动 create_task

### ISSUE-002
- 标题：任务中心过早展示中间态草稿
- 位置：`apps/api/routes/tasks.py`, `apps/api/routes/task_center.py`
- 症状：任务中心显示 `waiting_upload` / `ready_analyze`
- 当前判断：task-center 可见性规则需要重构
- 下一步：在 `R03` 中引入 `visible_in_task_center`

### ISSUE-003
- 标题：现有仓库无独立 migration 管理面
- 位置：`configs/database.py`
- 症状：仅靠 `Base.metadata.create_all()` 无法给已存在数据库补列
- 当前判断：本轮先用启动时加法式补列 + 显式脚本兜底
- 下一步：若后续 schema 变更继续增多，需要统一引入正式 migration 管理
