# Scheduler Harness

这个目录是任务调度系统的 Harness 工位，用来支持跨 session 的持续开发、测试准入和结果记录。

## 标准 artifact

- `app_spec.txt`: 规格、边界、成功标准
- `feature_list.json`: 功能拆解和完成状态
- `claude-progress.txt`: 每次 session 的工作记录
- `init.sh`: 环境检查、smoke test 和 release gate 入口
- `case_catalog.yaml`: 66 条发布准入用例的完整映射（F05 完成）
- `run_release_gate.py`: 完整的发布准入测试 runner（F06 完成）

## 使用方式

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/scheduler_plan

# 查看状态（自动检测下一个待完成的功能）
./init.sh status

# 仓库结构检查
./init.sh repo-check

# 快速冒烟测试
./init.sh smoke-test

# 完整的发布准入测试（生成详细报告）
./init.sh release-gate
# 或直接使用 Python runner
python run_release_gate.py
```

## Release Gate 报告

执行 `run_release_gate.py` 后会生成：

- `reports/release_gate_result_YYYYMMDD_HHMMSS.md`: 带时间戳的完整报告
- `reports/latest_result.md`: 最新报告的快捷方式

报告内容包括：
- P0/P1/P2 用例覆盖统计
- 测试通过率
- 阻断性失败列表
- 发布决策（PASS/FAIL）

## 开发原则

1. 先读 `app_spec.txt` 和 `feature_list.json`
2. 一次只做一个 feature
3. 先写测试，再补实现
4. 实现后更新 `feature_list.json` 与 `claude-progress.txt`
5. 保持任务在任何时刻都可恢复继续

## 当前状态

- F01 ✅ Harness Bootstrap - 完成
- F02 ✅ Scheduler Domain Core - 完成  
- F03 ✅ Persistence Bridge - 完成
- F04 ✅ FastAPI Endpoints - 完成
- F05 ✅ Release Gate Test Matrix (66 cases) - 完成
- F06 ✅ Harness Runner Reporting - 完成

所有 P0 和 P1 用例已通过测试，系统满足发布标准。
