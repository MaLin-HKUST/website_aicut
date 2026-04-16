# Worker Gateway + A-Scheduler Harness

这个目录只存放 Harness 追踪与验收资产，不存放正式产品代码。

正式代码始终放在主工程：
- `/Users/malin13/Documents/trae_projects/website_aicut/apps`
- `/Users/malin13/Documents/trae_projects/website_aicut/worker`
- `/Users/malin13/Documents/trae_projects/website_aicut/configs`

## 标准 artifacts

- `app_spec.txt`
- `feature_list.json`
- `claude-progress.txt`
- `init.sh`
- `case_catalog.yaml`
- `run_release_gate.py`
- `reports/RESULT_TEMPLATE.md`
- `artifacts/`
- `notes/`

## 工作规则

1. 一次只做一个 feature。
2. 每个 feature 使用独立 branch；并行开发时优先给每个 feature 配独立 worktree。
3. feature 开发过程中允许多次提交，但 feature 完成后必须至少有一个清晰的 feature commit，并完成该 feature 的验证。
4. 不把主工程已有的无关 dirty changes 混进 feature commit。
5. commit 时必须使用显式 pathspec，禁止 `git add .`、`git commit -a` 这类会吞入无关改动的做法。
6. 多个 feature 不直接在主开发分支上混合推进；先合并到集成分支，再统一联调和发布。
7. Docker 产物目录固定为：
   `/Volumes/XIAOMA-A-1T/docker_hub/WorkerGateway_and_Ascheduler`
8. 本次版本固定为 `0.0.3`。
9. 镜像 tar 文件名必须包含：
   - 组件名
   - 版本号
   - 时间戳
   - 可选短 commit sha

## Branch / Worktree / Merge 规则

### Branch 规则

- 每个 feature 一个 branch，例如：
  - `feature/F02-a-scheduler-runtime`
  - `feature/F06-worker-gateway-postgres`
- branch 只承载一个 feature 的改动，不跨 feature 混改。
- feature 未完成前，提交都留在该 feature branch 内。

### Worktree 规则

- 并行 coding agent 开发时，优先为每个 feature branch 建独立 worktree。
- 一个 worktree 只做一个 feature，避免不同 agent 共享同一工作目录。
- 同一 feature 的 write scope 之外的目录不进入暂存区。

### Commit 规则

- feature 开发期间可以有多个 commit，不要求只保留一个。
- feature 完成前必须完成：
  - feature 验证
  - 暂存区检查
  - 至少一个清晰的 feature commit
- commit 前固定检查：

```bash
git status --short
git diff --cached --name-only
```

- 只暂存当前 feature 的目录，例如：

```bash
git add apps/scheduler HarnessPlan/scheduler_AandW
```

### Merge 规则

- feature branch 通过 review 后，不直接当发布分支。
- 所有完成的 feature branch 先合并到集成分支，例如：
  - `integration/scheduler_AandW_0.0.3`
- 集成分支负责：
  - 联调
  - 镜像构建
  - release gate
- 发布产物只能从集成分支或其发布分支生成，不从零散 feature branch 直接生成。

### Dirty Worktree 规则

- 仓库存在历史或其他 agent 的脏改动时，不要求先清空工作区。
- 解决方式不是停工，而是：
  - 明确当前 feature 的 `write_scope`
  - 只暂存 `commit_scope`
  - 用 branch/worktree 隔离改动
- 若共享文件不可避免冲突，由集成人统一处理，不让多个 agent 直接抢写同一文件。

## 推荐命名

- `a-scheduler_0.0.3_YYYYMMDD_HHMMSS_<shortsha>.tar.gz`
- `worker-gateway_0.0.3_YYYYMMDD_HHMMSS_<shortsha>.tar.gz`

## 使用方式

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/scheduler_AandW

./init.sh status
./init.sh repo-check
./init.sh smoke-test
./init.sh feature-check F02
./init.sh release-gate
```

## 当前阶段

- 已完成：F01-F13
- 下一步：F14 Artifact Build And Version Recording
