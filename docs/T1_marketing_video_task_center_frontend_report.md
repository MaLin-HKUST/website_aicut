# T1 Marketing Video Task Center Frontend Report

## Summary

Updated the Marketing Video frontend so `/marketing-video` is a creation entry point and `/tasks` is the persistent management surface for Marketing Video workflows. Users can create one task, leave the page, open the task from `/tasks?taskId=...`, refresh without losing state, rename, stop queued/running tasks, archive cancelled/failed tasks, and download when succeeded.

Decision: `PASS_WITH_CONDITIONS`

Condition: local frontend gates passed; staging validation was not run.

## Changed Files

- `apps/web/components/marketing-video/workspace.tsx`
- `apps/web/components/task-center/user-tasks-shell.tsx`
- `apps/web/lib/marketing-video.ts`
- `apps/web/lib/task-center.ts`
- `apps/web/tests/marketing-video.spec.ts`
- `apps/web/tests/marketing-video-real-api.spec.ts`
- `docs/T1_marketing_video_task_center_frontend_report.md`

## Contract Decisions

- `/marketing-video` no longer treats progress/detail/download as the main experience. It creates the workflow and links to `/tasks?taskId=<workflow_id>`.
- Marketing Video workflows are fetched directly from `/api/marketing-video/workflows` and merged into the existing task center list.
- Smart Cut task center API behavior is preserved and still loaded independently.
- Marketing Video detail uses the three T1 node labels: 准备素材与基础视频, 智能匹配素材, 渲染成片.
- Mock mode mirrors the three-node T1 shape so local UX tests exercise the same surface as real API mode.

## Tests Run

```text
npm run build
-> PASS

npm run test:e2e -- marketing-video.spec.ts
-> PASS, 7 passed

NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
-> PASS, 7 passed, 1 skipped

git diff --check
-> PASS
```

## Pass / Fail

PASS_WITH_CONDITIONS.

## Known Gaps

- T1.5 staging validation was not run.
- Live Stage 5C browser smoke remains opt-in with `RUN_STAGE6C_LIVE_SMOKE=1` and was skipped.

## Spec Deviations

None.

## Handoff Notes

- Before promotion, run a staging browser smoke against the real B API for create/list/detail/rename/cancel/archive/refresh.
- Production frontend, Smart Cut production data, and production A were not touched.
