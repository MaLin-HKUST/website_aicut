# Agent 04 任务书：R07-R09 Preview 与 Finalize 升格

## 你的角色

你负责把工作台从 analyze 阶段继续推进到 preview 与 finalize，并把 finalize 的“升格为正式任务”语义做对。

你负责：

- `R07` Preview 页面内回显
- `R08` Finalize 升格为正式任务
- `R09` Finalize 后工作台清理

你不负责：

- `R04-R06` 的入口和 analyze 骨架
- 任务中心列表过滤
- 最终真实浏览器收口

## 开始时机

你必须在 Agent 03 的工作台骨架和 analyze 页面回显稳定后再开始。

简单判断标准：

- 页面已能恢复草稿
- analyze 后能看到 script 与 `audio_a`

## 必读上下文

1. [../README.md](../README.md)
2. [../03_前端状态机与页面行为.md](../03_前端状态机与页面行为.md)
3. [../04_任务中心可见性规则.md](../04_任务中心可见性规则.md)
4. [../task.json](../task.json)
5. [03_agent_R04_R06_前端工作台入口与Analyze.md](./03_agent_R04_R06_前端工作台入口与Analyze.md)
6. [../../30_preview_delaycut_issue_2026-04-20/README.md](../../30_preview_delaycut_issue_2026-04-20/README.md)
7. 仓库根 `AGENTS.md`

## 你要改哪些文件

优先写入范围：

- `apps/web/components/smart-cut/workspace.tsx`
- `apps/web/components/smart-cut/script-editor.tsx`
- `apps/web/lib/smart-cut.ts`
- finalize/preview 强相关 API 消费层

如确实需要，可改：

- `apps/api/routes/stages.py`
- 与 finalize 升格事务强相关的 API 代码

不要改：

- 任务中心列表查询
- 会话草稿核心数据模型
- Worker 算法实现本体

## 你要完成什么

### R07

1. 用户只能改删除线，不能改正文
2. 点击 `开始生成试听` 后，顶部状态条显示处理中
3. preview 完成后，右侧播放器更新为 `audio_b`

### R08

1. 用户选择输出规格
2. 点击 `开始生成视频`
3. 在同一事务里：
   - `visible_in_task_center = true`
   - 写入北京时间标题
   - 创建 finalize 调度任务

### R09

1. finalize 提交后，页面提示任务已进入任务列表
2. 当前工作台立即清空回初始态
3. 用户可以继续开始下一条

## 起点

当前问题：

- preview/试听和页面还没形成正确的单页闭环
- finalize 提交后工作台不会立即恢复初始态
- 任务中心升格时机和标题规则没有被固定实现

## 终点

主集成人接手时应能直接验证：

- preview 后 `audio_b` 出现在页面右侧
- finalize 后任务中心出现正式任务卡
- 当前工作台清空回初始态

## 你需要的验证

至少给：

- preview 成功后的页面证据
- finalize 提交后的 DB/API 状态证据
- 一个工作台已清空的页面证据

推荐验证：

- preview/finalize API 测试
- 相关前端交互测试

## 你回交时必须给我什么

严格按 [99_交付回交模板.md](./99_交付回交模板.md) 回交。

并补充：

- 你如何保证正文字符不可改
- 你如何把删除线转回 brace script
- 标题与北京时间是在前端生成还是后端生成

## Git 要求

- 建议分支名：
  - `feature/smart-cut-workspace-refactor-R07-R09-preview-finalize`
- 必须给出：
  - `branch`
  - `commit SHA`

## 阻塞规则

如果你发现：

- 当前 preview 契约还不稳定
- finalize 的事务边界不在你的可控范围内
- 需要更改 Worker 核心算法才能完成页面逻辑

不要私自扩 scope，直接报告阻塞。
