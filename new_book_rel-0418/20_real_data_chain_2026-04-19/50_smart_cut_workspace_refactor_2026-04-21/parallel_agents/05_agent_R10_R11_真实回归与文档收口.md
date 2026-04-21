# Agent 05 任务书：R10-R11 真实回归与文档收口

## 你的角色

你是最后一棒。你不负责拍脑袋改产品交互，你负责在前面实现基本收敛后，执行真实浏览器回归并把结论写回 codebook。

你负责：

- `R10` 真实浏览器回归
- `R11` 文档与状态收口

你不负责：

- 数据模型设计
- 页面骨架开发
- preview/finalize 交互本体开发

## 开始时机

你必须等到这些任务都已有一版实现后再开始：

- `R03`
- `R04`
- `R05`
- `R06`
- `R07`
- `R08`
- `R09`

没有这一前提，你的工作会退化成“发现所有东西都还没做好”。

## 必读上下文

1. [../README.md](../README.md)
2. [../05_测试与验收标准.md](../05_测试与验收标准.md)
3. [../task.json](../task.json)
4. [../../40_headed_browser_e2e_2026-04-21/README.md](../../40_headed_browser_e2e_2026-04-21/README.md)
5. [../../40_headed_browser_e2e_2026-04-21/task.json](../../40_headed_browser_e2e_2026-04-21/task.json)
6. [../../02_真实数据清单.md](../../02_真实数据清单.md)
7. [../../../基础网络信息和账号信息.md](../../../基础网络信息和账号信息.md)
8. 仓库根 `AGENTS.md`

## 你要改哪些文件

优先写入范围：

- `new_book_rel-0418/20_real_data_chain_2026-04-19/artifacts/...`
- `new_book_rel-0418/20_real_data_chain_2026-04-19/03_当前正式链路与缺口.md`
- `new_book_rel-0418/20_real_data_chain_2026-04-19/04_step_by_step执行计划.md`
- `new_book_rel-0418/10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md`
- `new_book_rel-0418/10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md`

必要时可补：

- 真实浏览器测试文件

不要改：

- 本轮核心业务逻辑实现
- 数据模型定义
- 任务中心规则

## 你要完成什么

### R10

1. 按 headed browser 真实跑 Smart Cut 全链路
2. 用真实样本：
   - `C2384_reencoded.mp4`
   - `ref.txt`
3. 检查 UI / API / DB / Worker / TOS 五个面

### R11

1. 把本轮真实结果回写到 codebook
2. 更新当前状态文档
3. 产出新的 artifacts 索引与总结

## 起点

前提是系统已进入“可真正测试”的状态。

## 终点

主集成人接手时应能直接看到：

- 一份新的真实浏览器 artifacts 目录
- 一组完整的执行证据
- 更新后的状态文档
- 清晰的剩余风险列表

## 你需要的验证

必须至少覆盖：

- 登录
- `/smart-cut`
- 上传
- analyze
- preview
- finalize
- `/tasks`
- 下载最终视频

并同步核对：

- API 状态
- 调度数据库状态
- Worker 日志
- TOS 对象

## 你回交时必须给我什么

严格按 [99_交付回交模板.md](./99_交付回交模板.md) 回交。

并补充：

- 本轮真实任务 ID
- 最终视频 key
- 哪一步如果失败，失败证据目录在哪
- 你更新了哪些文档

## Git 要求

- 建议分支名：
  - `feature/smart-cut-workspace-refactor-R10-R11-integration`
- 必须给出：
  - `branch`
  - `commit SHA`

## 阻塞规则

如果真实浏览器跑不通：

- 不要绕开问题继续写“成功结论”
- 必须把失败点、任务 ID、日志位置、接口结果、页面截图完整交回
