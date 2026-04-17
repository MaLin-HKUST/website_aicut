# rel0415 UI Harness

这个目录只存放 `rel0415` 用户端重设计的 Harness 追踪资产，不存放正式产品代码。

正式代码始终放在主工程：
- `/Users/malin13/Documents/trae_projects/website_aicut/apps/web`
- `/Users/malin13/Documents/trae_projects/website_aicut/doc/rel-0415-versionbook`

## 目标

把当前 `rel0415` 的用户端界面重做成旧截图认可的工作台形态：

- 独立中文登录页
- 登录后默认进入 `Welcome` 总览页
- 左侧固定任务栏
- 顶部摘要统计
- `TTS / Smart Cut / Tasks` 共用统一壳层

并且满足：

- 不改 admin 页面信息架构
- 不改后端 API、数据库和任务协议
- 新功能继续通过左侧任务栏进入对应页面

## 标准 artifacts

- `app_spec.txt`
- `feature_list.json`
- `claude-progress.txt`
- `init.sh`
- `run_release_gate.py`
- `notes/`
- `reports/`
- `artifacts/`
- `handover/`

## 工作规则

1. 一次只推进一个主 feature 到可验证状态。
2. 每个 feature 使用独立 branch；并行时优先每个 feature 配独立 worktree。
3. 禁止 `git add .`、`git commit -a`。
4. 只允许显式 pathspec 提交本 feature 的改动。
5. 所有 UI feature 先汇总到 `release/0415` 再做最终验收。

## 使用方式

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/rel0415-ui

./init.sh status
./init.sh repo-check
./init.sh smoke-test
./init.sh feature-check U05
./init.sh release-gate
```
