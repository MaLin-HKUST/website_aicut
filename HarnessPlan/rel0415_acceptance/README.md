# 0415 Acceptance Harness

这个目录只服务 `0415` 的最终验收轮次，不承担产品实现 backlog。

它的目标是把你刚刚重新定义的上线标准固定下来，并允许这轮验收长期、分 session、按 feature 持续推进：

1. Playwright 端到端自动化测试
2. 真实数据测试
3. 任务队列显示验证
4. 状态推进验证
5. 完成后下载验证
6. 排队情况验证

## 这轮 Acceptance 的边界

- 这是 **验收 harness**
- 不是功能开发 harness
- 产品代码仍在主工程下：
  - `apps/`
  - `worker/`
  - `configs/`
  - `scripts/`
- 当前实现 harness 仍在：
  - `HarnessPlan/rel0415`

## 当前已知真实数据记录

仓库中确认还保留了你之前给过的真实数据入口记录：

- `tests/test_cujiian/manual_case_config.json`
- `tests/test_cujiian/README.md`
- `doc/cujiian/粗剪的调度的测试/真实数据上线验收测试用例清单.md`
- `doc/cujiian/粗剪的调度的测试/真实数据上线验收执行记录表.md`

当前记录的真实数据路径是：

- 视频：`/Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4`
- 文案：`/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`

这说明：
- `记录还在`
- 但是否还能直接跑，要在本轮验收里重新做路径可读性检查

## Git 规则

这轮验收固定采用：

- `master`
  - 当前线上稳定主干
- `release/0415`
  - 当前 0415 集成分支
- `feature/0415-acceptance-*`
  - 本轮验收 feature 分支

规则：

1. 一个 acceptance feature 一个 branch
2. 并行时一个 feature 一个 worktree
3. 禁止 `git add .`
4. 禁止 `git commit -a`
5. 必须显式 pathspec
6. 验收通过后，修复和验收记录先回到 `release/0415`
7. 0415 最终确认通过后，再把 `release/0415` 收回 `master`

## 输出物

- `app_spec.txt`
- `feature_list.json`
- `claude-progress.txt`
- `init.sh`
- `case_catalog.yaml`
- `run_release_gate.py`
- `notes/current-status.md`
- `reports/RESULT_TEMPLATE.md`
- `handover/README.md`

## 当前阶段

- 已完成：`A01 Harness Bootstrap And Acceptance Scope Lock`
- 已完成：`A02 Real Data Inventory And Path Verification`
- 已完成：`A03 Playwright Live Route Reachability`
- 下一步：`A04 Playwright Smart Cut End To End`
