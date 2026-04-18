# Phase 3 Decision Record

- `phase`: 3
- `time`: 2026-04-18
- `operator`: Codex
- `inputs`:
  - `03_重建目标.md`
  - `09_当前资产清单与保留删除建议.md`
  - `10_重建执行清单.md`
  - 阶段 1 线上快照
  - 阶段 2 TOS 备份锚点
- `commands`:
  - 只读文档检查
  - 重建文档修订
- `network_ops`:
  - 本阶段无破坏性网络操作
  - 使用阶段 1 和阶段 2 已获取的远端事实作为输入
- `artifacts`:
  - `target_topology.md`
  - `service_ownership_matrix.md`
  - `phase3_decision_record.md`
- `verification`:
  - 已形成明确的“正式保留 / 过渡保留 / 必须退出”清单
  - 已明确 TOS 工具链转正要求
  - 已把“备份以 TOS 为主”写入阶段文档和目标文档
- `rollback_anchor`:
  - 沿用阶段 2 备份锚点：`backup/a-machine/pre_rebuild/pre_rebuild_20260418_224329`
- `status`: passed

## 阶段 3 决议

1. A 机器长期只保留网站主服务器与调度中心。
2. Worker Gateway 与 Smart Cut Worker 最终都必须迁回 Worker 机器。
3. `/tmp/tos_uploader_runtime` 当前不删，后续必须转正为正式工具目录。
4. 备份真相以 TOS 为主，不再把本机长期备份当目标。
5. 除正式运行面、正式工具、正式配置、正式数据、正式回滚锚点之外，其余对象全部进入待删除清单。
