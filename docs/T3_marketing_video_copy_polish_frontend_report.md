# T3 Marketing Video Copy Polish Frontend Report

## Summary

Updated the Marketing Video creation page customer-facing copy so users see a Chinese mode label and TXT input guidance without raw internal task type, RBZJ/KDT, or TONGAN wording in the requested copy block.

Decision: PASS

## Preflight

- Frontend worktree path: `/Users/malin13/Documents/trae_projects/website_aicut_worktrees/T2_5_status_release`
- Initial observed branch before task branch creation: `rc/T2-status-display-release`
- Initial dirty status: clean
- Base branch: `integration/T-current`
- Base commit: `39d2780da39547217fadcdab170b110a68d760c1`
- Task branch: `feature/T3-marketing-video-copy-polish-ui`
- Backend source needed: no

## Changed Files

- `apps/web/components/marketing-video/workspace.tsx`
- `apps/web/tests/marketing-video.spec.ts`
- `docs/T3_marketing_video_copy_polish_frontend_report.md`

## Contract Decisions

- Replaced only the three requested visible strings.
- Preserved the user-provided spacing in `创建 标准营销视频任务`.
- Left API request and fixture `task_type: "std_marketing_video"` values unchanged because this task explicitly excludes API/backend contract changes.
- Did not change page layout, upload behavior, task-center behavior, company gate logic, workflow runtime, or release artifacts.

## Tests Run

```text
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/T2_5_status_release/apps/web
npm run build
```

Result: PASS.

```text
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/T2_5_status_release/apps/web
npm run test:e2e -- marketing-video.spec.ts
```

Result: PASS, 7 passed.

```text
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/T2_5_status_release/apps/web
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
```

Result: PASS, 7 passed, 1 skipped. The skipped test is the existing live workflow smoke in the test suite.

```text
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/T2_5_status_release
git diff --check
```

Result: PASS.

## Text Verification

Source UI verification:

- `apps/web/components/marketing-video/workspace.tsx` contains `标准视频模式`.
- `apps/web/components/marketing-video/workspace.tsx` contains `输入短视频的文案(txt文件格式)`.
- `apps/web/components/marketing-video/workspace.tsx` contains `上传短视频的文案并创建 标准营销视频任务。创建后可以离开本页，后续进度、停止、改名和下载都在任务中心处理。`
- `apps/web/components/marketing-video/workspace.tsx` no longer contains `只支持一个 TXT 文案文件。RBZJ/KDT IP 模式暂未开放。`
- `apps/web/components/marketing-video/workspace.tsx` no longer contains `上传一个 TXT 文案并创建 TONGAN 标准营销视频任务。`
- The visible mode badge no longer renders `std_marketing_video`.

Notes:

- `std_marketing_video` still exists in request payloads, adapters, and tests as an internal API contract value. It was intentionally not changed.
- `marketing-video.spec.ts` includes negative assertions for the two old visible sentences to prevent regression.

## Pass / Fail

PASS.

## Known Gaps

- No production deployment was performed in T3.
- No staging or production browser validation was performed because this is not a release/artifact task.
- The real-mode live workflow smoke remains skipped by the existing test suite.

## Spec Deviations

None.

## Handoff Notes

- If this copy must become visible on `https://xiaomajianji.cn/marketing-video`, run a separate T3.5 release/artifact task.
- Rollback source command after merge would be `git revert <T3-commit>` on the integration/release branch.
