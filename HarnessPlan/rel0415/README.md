# 0415 Version Harness

这个目录只存放 `0415` 版本的 Harness 追踪资产，不存放正式产品代码。

正式代码始终放在主工程：
- `/Users/malin13/Documents/trae_projects/website_aicut/apps`
- `/Users/malin13/Documents/trae_projects/website_aicut/configs`
- `/Users/malin13/Documents/trae_projects/website_aicut/server_sync/20260415_a_machine_snapshot/code_and_data/apps/web`
- `/Users/malin13/Documents/trae_projects/website_aicut/doc/rel-0415-versionbook`

## 目标

`0415` 的目标是把两份交接页面真正拼进现网站点：

- `Smart Cut`：普通用户三段工作页
- `任务中心`：独立入口，用户和 admin 页面结构统一、字段不同

并且满足：

- 不破坏现网 `admin + TTS + 登录`
- Smart Cut 点击“生成视频”后，状态跟踪和下载进入任务中心
- 不再依赖 Nginx 注入和静态占位页

## 当前 grounded 结论

1. `website_aicut` 仓库当前没有正式 `apps/web` 前端代码。
2. A 机现网 Next 基线在：
   - `/Users/malin13/Documents/trae_projects/website_aicut/server_sync/20260415_a_machine_snapshot/code_and_data/apps/web`
3. Smart Cut 交接件与现网同为 `Next App Router`，可以直接迁移。
4. 任务中心交接件来自 `Vite + React Router`，不能直接贴进现网，必须做页面级移植。
5. `0415` 要做的是真实可用版本，不是 mock/demo 预览版。

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
- `handover/`

## 工作规则

1. 一次只做一个 feature。
2. 每个 feature 使用独立 branch；并行开发时优先给每个 feature 配独立 worktree。
3. feature 开发过程中允许多次提交，但 feature 完成后必须至少有一个清晰的 feature commit，并完成该 feature 的验证。
4. 不把主工程已有的无关 dirty changes 混进 feature commit。
5. commit 时必须使用显式 pathspec，禁止 `git add .`、`git commit -a`。
6. 所有 0415 feature 先汇总到 `release/0415`，测试通过后再回合并 `master`。

## 3-Agent 主切分

- Agent 1：真实后端链路、Smart Cut API、任务中心 API、E2E 联调
- Agent 2：任务中心页面移植与用户/admin 视图
- Agent 3：Smart Cut 页面迁移与前后端连接

协作规则：

- 一个 feature 一个 branch
- 并行时一个 feature 一个 worktree
- 不允许多个 agent 直接抢写同一主页面文件
- 共享 contract 先冻结，再分别实现

## 使用方式

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/rel0415

./init.sh status
./init.sh repo-check
./init.sh smoke-test
./init.sh feature-check F03
./init.sh release-gate
```

## 当前阶段

- 已完成：F01 Harness Bootstrap And Source Lock
- 已完成：F02 Recover Live Next Web Baseline Into Repo
- 已完成：F03 Smart Cut Next Page Migration
- 已完成：F04 Task Center Next Page Migration
- 已完成：F05 Welcome And Admin Entry Integration
- 已完成：F06 Smart Cut API Contract Alignment
- 已完成：F07 Task Center User And Admin API
- 已完成：F08 Smart Cut To Task Center Transition Wiring
- 已完成：F09 Frontend Build Green On 0415 Baseline
- 下一步：F10 Server Deploy To release/0415 Test Slot
