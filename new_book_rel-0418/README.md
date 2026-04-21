# website_aicut 新一代项目手册（rel-0418）

本文回答什么问题：

- 这套新文档如何组织
- 哪些文档是长期规则，哪些文档只服务于 2026-04-18 重建专项
- 不同类型的 Coding Agent 该先读什么

## 文档分层

本目录分为两层：

1. `00_system_knowledge/`
- 长期可复用的系统知识层
- 定义系统是什么、架构如何分层、职责边界、发布规则、备份规则、Agent 禁区
- 后续所有 Agent 都应优先阅读这一层

2. `10_rebuild_2026-04-18/`
- 2026-04-18 A 机器重建专项层
- 解释当前线上为什么混乱、当前有哪些运行面、为什么要重建、怎么重建、怎么验收、怎么回滚
- 只有参与本轮重建或后续清尾的 Agent 需要阅读这一层

3. `20_real_data_chain_2026-04-19/`
- 真实数据链路专项层
- 解释如何在当前正式运行面上，用真实样本跑通 Smart Cut 全链路，并把这轮结果沉淀为后续可复用的执行与证据规范
- 只有参与真实数据联调、证据落档、热补收口与发布收口的 Agent 需要阅读这一层

## 阅读入口

### 普通功能开发 Agent

按这个顺序阅读：

1. [00_system_knowledge/README.md](./00_system_knowledge/README.md)
2. [00_system_knowledge/01_系统定义.md](./00_system_knowledge/01_系统定义.md)
3. [00_system_knowledge/02_系统架构与职责边界.md](./00_system_knowledge/02_系统架构与职责边界.md)
4. [00_system_knowledge/06_Agent工作规则与禁区.md](./00_system_knowledge/06_Agent工作规则与禁区.md)
5. 如果要协作前端 coding agent，先读 [00_system_knowledge/08_前端协作模板.md](./00_system_knowledge/08_前端协作模板.md)
6. 如果要理解前端上线唯一规则，读 [00_system_knowledge/11_前端发布单一路径.md](./00_system_knowledge/11_前端发布单一路径.md)
7. 如果要做前端上线、截图验收、Playwright 线上验收，读 [00_system_knowledge/09_前端页面修改上线Runbook.md](./00_system_knowledge/09_前端页面修改上线Runbook.md)
8. 如果要直接复制给前端 coding agent 的任务模板或交付模板，读 [00_system_knowledge/10_前端CodingAgent交付纯模板.md](./00_system_knowledge/10_前端CodingAgent交付纯模板.md)
6. 按任务需要继续读发布、备份、代码结构、术语表

### 架构、运维、发布、重建 Agent

按这个顺序阅读：

1. `00_system_knowledge/` 全部核心文档
2. [10_rebuild_2026-04-18/README.md](./10_rebuild_2026-04-18/README.md)
3. `10_rebuild_2026-04-18/` 下的当前现状、重建目标、重建步骤、验收回滚

### 真实数据联调 / 发布收口 Agent

按这个顺序阅读：

1. `00_system_knowledge/` 核心文档
2. [10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md](./10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md)
3. [10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md](./10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md)
4. [20_real_data_chain_2026-04-19/README.md](./20_real_data_chain_2026-04-19/README.md)
5. 如果任务是 Smart Cut 工作台交互生命周期重构，继续读 [20_real_data_chain_2026-04-19/50_smart_cut_workspace_refactor_2026-04-21/README.md](./20_real_data_chain_2026-04-19/50_smart_cut_workspace_refactor_2026-04-21/README.md)

## 与旧文档的关系

- 旧 `book/` 目录保留为历史参考
- 新规则、新架构边界、新发布与备份约束，全部以 `new_book_rel-0418/` 为准
- 如果旧 `book/` 与这里冲突，以这里为准

## 目录

- [00_system_knowledge/README.md](./00_system_knowledge/README.md)
- [10_rebuild_2026-04-18/README.md](./10_rebuild_2026-04-18/README.md)
- [20_real_data_chain_2026-04-19/README.md](./20_real_data_chain_2026-04-19/README.md)
- [20_real_data_chain_2026-04-19/50_smart_cut_workspace_refactor_2026-04-21/README.md](./20_real_data_chain_2026-04-19/50_smart_cut_workspace_refactor_2026-04-21/README.md)
- [00_system_knowledge/08_前端协作模板.md](./00_system_knowledge/08_前端协作模板.md)
- [00_system_knowledge/09_前端页面修改上线Runbook.md](./00_system_knowledge/09_前端页面修改上线Runbook.md)
- [00_system_knowledge/10_前端CodingAgent交付纯模板.md](./00_system_knowledge/10_前端CodingAgent交付纯模板.md)
- [00_system_knowledge/11_前端发布单一路径.md](./00_system_knowledge/11_前端发布单一路径.md)

## 当前线上状态快速入口

如果你不是来研究整个重建过程，而是要快速知道“现在系统跑在哪里、谁在提供服务、当前 release 是哪个 commit”，优先读：

1. [10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md](./10_rebuild_2026-04-18/11_2026-04-19_当前系统状态.md)
2. [10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md](./10_rebuild_2026-04-18/12_2026-04-19_当前Release与证据索引.md)
3. [10_rebuild_2026-04-18/rebuild-artifacts/20260419_phase8_release/final_release_manifest.json](./10_rebuild_2026-04-18/rebuild-artifacts/20260419_phase8_release/final_release_manifest.json)

这三份文档是“当前线上状态”的单一真相入口。

## 当前真实数据专项入口

如果你下一步的任务是：

- 用真实样本跑 Smart Cut
- 补真实数据证据
- 把当前热补链路继续收口

优先读：

1. [20_real_data_chain_2026-04-19/README.md](./20_real_data_chain_2026-04-19/README.md)
2. [20_real_data_chain_2026-04-19/04_step_by_step执行计划.md](./20_real_data_chain_2026-04-19/04_step_by_step执行计划.md)
3. [20_real_data_chain_2026-04-19/05_证据清单与产物目录.md](./20_real_data_chain_2026-04-19/05_证据清单与产物目录.md)

## 本轮重建的推荐入口

如果你是本轮重建 Agent，建议直接按这个顺序进入：

1. `README.md`
2. `00_system_knowledge/README.md`
3. `10_rebuild_2026-04-18/README.md`
4. `基础网络信息和账号信息.md`
5. `10_rebuild_2026-04-18/09_当前资产清单与保留删除建议.md`
6. `10_rebuild_2026-04-18/10_重建执行清单.md`

## 对 Agent 的直接指令

- 进入本项目后，不要直接根据历史对话或零散代码猜系统形态。
- 先从本目录开始读，再决定服务应该放在哪台机器、数据库应该写到哪里、发布应该怎么做。
- 如果你要改动系统边界、发布流程、备份流程，必须先更新本目录的相关文档。
- 本轮执行类 Agent 需要额外读取 `基础网络信息和账号信息.md`，它是网络与账号的单一真相入口。
- 如果你要把页面截图交给前端 coding agent 改版，先看 `00_system_knowledge/08_前端协作模板.md`，实际复制时直接使用 `00_system_knowledge/10_前端CodingAgent交付纯模板.md`。
- 如果你要把前端修改真正上线，并确认用户在正式站看到什么，先按 `00_system_knowledge/11_前端发布单一路径.md` 确认原则，再按 `00_system_knowledge/09_前端页面修改上线Runbook.md` 执行。
