# T2 Marketing Video Task Status Display Frontend Report

## Summary

Updated `/tasks` Marketing Video rendering so task cards and node rows use the product display contract:

- Active node status rows show Chinese labels.
- Attempt labels are Chinese.
- Running workflow summaries without an active subtask show `排队中`, not `执行中`.
- Multiple Marketing Video cards can coexist while only the card with an active subtask shows `执行中`.

Decision: `PASS_WITH_CONDITIONS`

Condition: local frontend build/E2E passed; staging validation was not run.

## Changed Files

- `apps/web/lib/marketing-video.ts`
- `apps/web/components/task-center/user-tasks-shell.tsx`
- `apps/web/tests/marketing-video-real-api.spec.ts`
- `docs/T2_marketing_video_task_status_display_frontend_report.md`

## Contract Decisions

- Added `formatMarketingVideoSubtaskStatus(status, attempt)`.
- Added `deriveMarketingVideoDisplayQueueStatus(workflowOrSummary)`.
- Frontend prefers backend `display_status`; when detail subtasks are available, it can derive active execution from `running`, `accepted`, or `dispatching`.
- Unknown node statuses render `未知状态` instead of leaking raw backend strings.

## Tests Run

```text
npm run build
-> PASS

npm run test:e2e -- marketing-video.spec.ts
-> PASS, 7 passed

NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
-> PASS, 9 passed, 1 skipped

git diff --check
-> PASS
```

## Pass / Fail

`PASS_WITH_CONDITIONS`

## Known Gaps

- B staging browser validation was not run.
- Pre-existing untracked `apps/web/test-results/` remains in the worktree and was not modified intentionally.

## Spec Deviations

None.

## Handoff Notes

- This is a frontend/API display-contract fix only. No production deploy or release artifact was produced.
