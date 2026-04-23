# Branch Strategy

## 原则

这次重构不要继续把提交混在旧的 `feature/smart-cut-workspace-refactor-R10-R11-integration` 分支里。

当前已经切出的专项执行分支：

- `feature/smart-cut-taskcard-refactor`

推荐：

- 主分支：
  - `feature/smart-cut-taskcard-refactor`
- 大任务分支：
  - `feature/smart-cut-taskcard-refactor-L02`
  - `feature/smart-cut-taskcard-refactor-L03`
  - `feature/smart-cut-taskcard-refactor-L04`
  - `feature/smart-cut-taskcard-refactor-L05`
  - `feature/smart-cut-taskcard-refactor-L06`
  - `feature/smart-cut-taskcard-refactor-L07`

## worktree

推荐新 worktree：

- `/Users/malin13/Documents/trae_projects/website_aicut_worktrees/website_aicut-smartcut-taskcard-refactor`

## 提交规则

- 每个 commit 必须映射到：
  - `large_task_id`
  - `small_task_id`
- 每个 commit 后都要同步更新：
  - 总包 `progress.md / progress.json`
  - 对应大任务目录下的 `progress.md / progress.json`

## 禁止

- 不要再把新任务卡重构提交混进 `R10-R11` 历史语义里
- 不要在没有回写 codebook 进度前连续堆多次无记录提交
