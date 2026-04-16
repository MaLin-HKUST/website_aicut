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
- `F03` 已完成：Smart Cut Next 页面、组件、前端适配层已经迁入 `apps/web`，并通过了前端构建。
- `F04` 已完成：任务中心已在 Next 里重建为正式页面壳，不再依赖 Vite 路由、store 或旧 UI 体系。
- `F05` 已完成：welcome 已增加 Smart Cut / 任务中心入口，admin 已增加 `/admin/tasks` 入口。
- `F06` 已完成：Smart Cut 已具备 list / edits / upload-direct / detail contract，并完成了前端 helper 对齐。
- `F07` 已完成：任务中心已具备用户 / admin 两套真实列表接口，前端已切到真实数据适配层。
- `F08` 已完成：Smart Cut finalize 后会跳转到任务中心，并通过 query 选中对应任务；proxy 已具备 legacy / smart-cut 双后端分流。
- `F09` 已完成：当前 0415 前端基线 `npm --prefix apps/web run build` 通过。
- 下一步是 `F10`：把这套前后端代码部署到 `release/0415` 测试位，并接入 A 机与 Worker1 做服务器联调。
