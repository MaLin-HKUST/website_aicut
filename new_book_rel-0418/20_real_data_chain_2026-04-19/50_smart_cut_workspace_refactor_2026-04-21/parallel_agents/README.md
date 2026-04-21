# Smart Cut 并行开发入口

本文回答什么问题：

- 这次 Smart Cut 工作台重构应该拆给多少个并行 coding agent
- 每个 agent 什么时候开始，负责哪些 `R` 任务，能改哪些文件
- 每个 agent 必须先读哪些上下文、遵守哪些 codebook 规则
- 每个 agent 做完后必须按什么格式把结果交回主集成人

## 适用范围

这个目录只服务本专项：

- [../README.md](../README.md)
- [../task.json](../task.json)

它不是通用前端协作模板，也不是通用后端协作模板。

## 总体拆分

本轮建议开 **5 个并行 coding agent**。

1. Agent 01：`R01-R02`
   - 数据模型与会话草稿接口契约
2. Agent 02：`R03`
   - 任务中心可见性与历史空任务隐藏
3. Agent 03：`R04-R06`
   - `/smart-cut` 入口、草稿恢复、analyze 结果回显
4. Agent 04：`R07-R09`
   - preview 页面内回显、finalize 升格、工作台复位
5. Agent 05：`R10-R11`
   - 真实浏览器回归、文档与证据收口

## 阅读顺序

给每个 agent 发任务前，先让它读：

1. [../../README.md](../../README.md)
2. [../README.md](../README.md)
3. [../task.json](../task.json)
4. [00_并行开发总协调.md](./00_并行开发总协调.md)
5. 对应自己的 agent 任务书
6. [99_交付回交模板.md](./99_交付回交模板.md)

## 文件列表

- [00_并行开发总协调.md](./00_并行开发总协调.md)
- [01_agent_R01_R02_数据与接口契约.md](./01_agent_R01_R02_数据与接口契约.md)
- [02_agent_R03_任务中心可见性.md](./02_agent_R03_任务中心可见性.md)
- [03_agent_R04_R06_前端工作台入口与Analyze.md](./03_agent_R04_R06_前端工作台入口与Analyze.md)
- [04_agent_R07_R09_Preview与Finalize升格.md](./04_agent_R07_R09_Preview与Finalize升格.md)
- [05_agent_R10_R11_真实回归与文档收口.md](./05_agent_R10_R11_真实回归与文档收口.md)
- [99_交付回交模板.md](./99_交付回交模板.md)

## 对主集成人的直接指令

- 不要把多个 agent 写同一组文件的权限重叠分配出去。
- 先发 `Agent 01`，等契约层稳定后，再放开其余 agent 的实际编码。
- 所有 agent 的回交都必须经过 [99_交付回交模板.md](./99_交付回交模板.md)。
- 缺 `branch / commit SHA / 改动文件列表 / 验证命令` 任一项，视为未完成交付。
