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
- `L03` 已启动：
  - `start task`
  - `runs` 查询接口
- `L04` 已启动：
  - task center 优先按 `company_id` 过滤

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
- 新增最小验证：
  - `tests/test_task_card_schema.py`

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
- `apps/web/lib/task-center.ts`
  - 前端 task-center 查询支持 `companyId`
- `tests/test_task_card_schema.py`
  - 验证新表和新增字段
- `tests/test_rel0415_api.py`
  - 回归 `start task` / `runs` / company filter

## 已知风险

- 这一步完成的是 **可执行设计包**，不是重构代码本身
- 当前仓库业务代码仍然是旧隐藏草稿模型
- `L02-L04` 只完成了第一批基础设施，旧 draft 流程还在
- `L05-L07` 尚未开始真正实现
- `L00` 的历史提交仍来自旧分支，但后续实现已经切到 `feature/smart-cut-taskcard-refactor`
