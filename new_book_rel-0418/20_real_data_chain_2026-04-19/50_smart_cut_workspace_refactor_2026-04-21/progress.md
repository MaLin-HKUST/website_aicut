# Smart Cut Workspace Refactor Progress

## 当前阶段

- `R01-R02` 已编码并完成最小回归验证
- `Agent 01` 回交已完成审查，契约层可作为后续开发基线
- `Agent 02` 回交已完成审查，`R03` 可接受
- `Agent 03` 回交已完成审查，`R04-R06` 可接受
- 专项包已建立
- `R07-R09` 可以开始推进

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
- 完成 `Agent 01` 回交审查，确认 `branch / commit SHA / 改动文件 / 验证命令` 均可核对
- 完成 `Agent 02` 回交审查，确认任务中心过滤与 backfill 脚本交付完整
- 完成 `Agent 03` 回交审查，确认 `/smart-cut` 入口不再自动建空任务，analyze 结果可在当前页面回显

## 正在进行

- 主集成人评估 `configs/database.py` 的运行时补列策略是否原样集成
- 等待放行 `Agent 04`

## 阻塞项

- 无硬阻塞
- 注意：`configs/database.py` 的加法式补列实现需要在主线集成前单独复核

## 决策记录

- Smart Cut 按“同一登录会话内 1 个草稿”实现
- 退出登录后旧草稿失效
- finalize 前任务不进入任务中心
- analyze 后页面必须直接展示 `audio_a`
- preview 后页面必须直接展示 `audio_b`
- 并行开发按 5 个 agent 分工执行
- Agent 01 先行锁定契约，其余 agent 按依赖关系启动
- `commit 51071188253984779ca7ce9bce1d7ce42bad1919` 作为当前 `R01-R02` 契约基线
- `commit 380baddf7c61c0d0dd4630eb1c1bea4a79c3044c` 作为当前 `R03` 任务中心可见性基线
- `commit a00466106aeda2ee2877ac20c27dcdce0609baea` 作为当前 `R04-R06` 工作台入口与 analyze 回显基线

## 需要同步给其他 Agent 的上下文

- 这不是局部前端修补，而是交互生命周期重构
- 不要再沿用“点击 `/smart-cut` 立即 create_task” 的旧语义
- 不要让 task-center 继续显示 `waiting_upload` 等中间态

## 最近一次验证结果

- `pytest tests/test_rel0415_api.py`
- current draft / ensure draft 已验证同会话复用、跨会话隔离、缺失会话时报错
- finalize 已验证同次提交内写入标题并切换 `visible_in_task_center=true`
- 已核对 `branch=feature/smart-cut-workspace-refactor-R01-R02-contract`
- 已核对 `commit SHA=51071188253984779ca7ce9bce1d7ce42bad1919`
- 已核对 `branch=feature/smart-cut-workspace-refactor-R03-task-center-visibility`
- 已核对 `commit SHA=380baddf7c61c0d0dd4630eb1c1bea4a79c3044c`
- 已核对 `R03` 改动范围集中在 `task_center.py`、backfill 脚本、测试与专项检查文档
- 已核对 `branch=feature/smart-cut-workspace-refactor-R04-R06-draft-workspace`
- 已核对 `commit SHA=a00466106aeda2ee2877ac20c27dcdce0609baea`
- 已核对 `a004661` 自身只包含 5 个前端文件改动，没有把 `R03` 一起打包进提交
- 已核对验证命令：
  - `cd apps/web && npx tsc --noEmit`
  - `cd apps/web && npx playwright test tests/smart-cut.spec.ts --reporter=list`

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

### ISSUE-004
- 标题：Agent 01 的 write scope 比原任务书略宽
- 位置：`apps/api/routes/stages.py`, `configs/database.py`
- 症状：为 finalize 升格事务和补列落地，提交超出最初最窄写入范围
- 当前判断：扩 scope 有理由，但主集成人需要在合并前逐项确认这些改动不踩后续 Agent 02/03 的责任边界
- 下一步：主集成人在正式集成 `R01-R02` 时对这两处做额外审阅

### ISSUE-005
- 标题：Agent 02 的 backfill 脚本尚未在真实历史库执行
- 位置：`scripts/rel0415/backfill_smart_cut_task_center_visibility.py`
- 症状：当前只完成测试与脚本交付，没有对生产/真实 PostgreSQL 历史库做实际回填
- 当前判断：实现可接受，但上线前必须明确回填执行策略
- 下一步：在主线集成或上线前由主集成人决定何时执行 backfill

### ISSUE-006
- 标题：Agent 03 在前端保留了本地缓存 fallback
- 位置：`apps/web/components/smart-cut/workspace.tsx`
- 症状：当前为了兼容契约尚未完全落地，工作台会对同用户名保留本地缓存兜底
- 当前判断：短期可接受，但在契约稳定后应评估是否删掉，避免和服务端草稿语义双轨并存
- 下一步：在主集成人集成 `R04-R06` 时复核是否继续保留

### ISSUE-007
- 标题：Agent 03 未处理 `welcome -> /tts` 的既有导航失败
- 位置：`apps/web/tests/rel0415-user-navigation.spec.ts`
- 症状：该测试存在更早的旧失败，不属于本次 Smart Cut 入口重构直接引入
- 当前判断：不阻塞接收 `R04-R06`，但不要把它误判成这次改动的新问题
- 下一步：单独归档为已有历史问题，不在本专项里扩散修
