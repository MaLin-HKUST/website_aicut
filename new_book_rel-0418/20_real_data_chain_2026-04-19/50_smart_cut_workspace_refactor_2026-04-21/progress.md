# Smart Cut Workspace Refactor Progress

## 当前阶段

- `R00-R02` 规划完成
- 专项包已建立
- 尚未开始代码实现

## 已完成任务

- 建立专项目录
- 写入目标交互、数据模型、前端状态机、任务中心规则、验收标准
- 写入 `task.json`
- 建立 `progress.md` 与 `progress.json`

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

## 需要同步给其他 Agent 的上下文

- 这不是局部前端修补，而是交互生命周期重构
- 不要再沿用“点击 `/smart-cut` 立即 create_task” 的旧语义
- 不要让 task-center 继续显示 `waiting_upload` 等中间态

## 最近一次验证结果

- 当前专项文档已落地
- `task.json` 结构待做 JSON 解析校验

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
