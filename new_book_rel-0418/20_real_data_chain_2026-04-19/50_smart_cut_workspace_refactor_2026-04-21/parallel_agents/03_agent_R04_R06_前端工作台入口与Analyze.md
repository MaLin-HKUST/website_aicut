# Agent 03 任务书：R04-R06 前端工作台入口与 Analyze 回显

## 你的角色

你负责把 `/smart-cut` 改成真正的“会话草稿工作台”，并且让 analyze 结果直接回到当前页面。

你负责：

- `R04` Smart Cut 页面入口重构
- `R05` Upload 段会话恢复
- `R06` Analyze 页面内回显

你不负责：

- 任务中心可见性过滤
- preview/finalize 的后续行为
- 最终集成验收

## 开始时机

你必须在 Agent 01 的契约被主集成人接受后再开始。

你可以和 Agent 02 并行，但不要修改 Agent 02 的写入范围。

## 必读上下文

1. [../README.md](../README.md)
2. [../03_前端状态机与页面行为.md](../03_前端状态机与页面行为.md)
3. [../02_数据模型与接口重构.md](../02_数据模型与接口重构.md)
4. [../task.json](../task.json)
5. [01_agent_R01_R02_数据与接口契约.md](./01_agent_R01_R02_数据与接口契约.md)
6. [../../../00_system_knowledge/09_前端页面修改上线Runbook.md](../../../00_system_knowledge/09_前端页面修改上线Runbook.md)
7. 仓库根 `AGENTS.md`

## 你要改哪些文件

优先写入范围：

- `apps/web/app/smart-cut/page.tsx`
- `apps/web/components/smart-cut/workspace.tsx`
- `apps/web/components/smart-cut/script-editor.tsx`
- `apps/web/lib/smart-cut.ts`
- 相关前端测试

如确实需要，可改：

- 与 Smart Cut 页面强相关的 API schema 消费层

不要改：

- 任务中心查询逻辑
- Worker 算法逻辑
- preview/finalize 任务提交语义

## 你要完成什么

### R04

1. 删除 `/smart-cut` 进入即 `create_task`
2. 页面初始化时恢复当前会话草稿
3. 支持无 `taskId` 的草稿工作台模式

### R05

1. 用户上传视频/文案后，草稿状态能在同会话恢复
2. 用户切页、刷新、关标签后重进，只要没 logout，状态仍在

### R06

1. 点击 `开始分析` 后，顶部状态栏显示处理中提示
2. analyze 完成后，页面下方立即显示删除线脚本
3. 右侧立即显示 `audio_a` 播放器

## 起点

当前问题：

- `SmartCutLandingPage` 自动建任务
- 页面不是草稿工作台，而是“后台任务代理”
- analyze 完成后，script/audio 没有自然回当前页面

## 终点

主集成人接手时应能直接验证：

- 多次点“智能剪气口”不再新增空任务
- 上传状态在同会话内可恢复
- analyze 后页面直接显示脚本和 `audio_a`

## 你需要的验证

至少给：

- 类型检查
- Smart Cut 页面相关测试
- 一个“多次进入 `/smart-cut` 不再建任务”的证据
- 一个“analyze 后页面显示 script + audio_a”的证据

如果你能跑页面级测试，优先补：

- Smart Cut 页面单测/集成测试
- Playwright 或等价前端交互 smoke

## 你回交时必须给我什么

严格按 [99_交付回交模板.md](./99_交付回交模板.md) 回交。

并补充：

- 你是否改了 URL 模式
- 你是否引入了新的页面状态机
- 你是否新增了“草稿恢复失败”的空态/错误态

## Git 要求

- 建议分支名：
  - `feature/smart-cut-workspace-refactor-R04-R06-draft-workspace`
- 必须给出：
  - `branch`
  - `commit SHA`

## 阻塞规则

如果你发现：

- 当前接口无法支持页面恢复
- `audio_a` 无法从现有 task detail 拿到
- 页面必须强依赖任务中心改造才能继续

你不要自己扩到 Agent 02 或 Agent 04 的职责里，直接把阻塞交回来。
