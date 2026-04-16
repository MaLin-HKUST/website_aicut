# rel0415 Current Status

## Grounded baseline

- 当前仓库里已经有正式 `apps/web` 主工程前端。
- A 机现网 Next 基线位于：
  `/Users/malin13/Documents/trae_projects/website_aicut/server_sync/20260415_a_machine_snapshot/code_and_data/apps/web`
- 当前仓库后端主线位于：
  - `apps/api`
  - `apps/scheduler`
  - `apps/models`
  - `apps/services`
  - `configs`

## Handover sources

- Smart Cut handover:
  `/Users/malin13/Documents/trae_projects/website_aicut/doc/rel-0415-versionbook/handover/SmartCut_接手拼装交接说明.md`
- Task Center handover:
  `/Users/malin13/Documents/trae_projects/website_aicut/doc/rel-0415-versionbook/handover/task-center-handover.md`

## Key integration conclusions

1. Smart Cut handover is `Next App Router` and should be migrated directly into the recovered Next baseline.
2. Task Center handover is `Vite + React Router` and must be rebuilt as a Next page, not copied verbatim.
3. The temporary Smart Cut Nginx/static patch must remain until the real Next route is live, then be removed.
4. 0415 is a real release target, not a mock/demo preview branch.
5. `release/0415` is the integration branch for this harness.

## Current next move

- `F02` 已完成：现网 Next 基线已经正式回收到 `apps/web`，并通过了 `npm --prefix apps/web run build`。
- `F03` 直接迁移 Smart Cut Next 页面与组件。
- `F04` 在 Next 里重建任务中心页面壳，不直接复制 Vite 页面。
