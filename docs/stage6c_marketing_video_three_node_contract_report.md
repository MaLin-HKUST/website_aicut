# Stage 6C Marketing Video Three-Node Contract Report

## Summary

PASS.

Refreshed the Marketing Video frontend for the verified Stage 5C TONGAN route:
`tongan_pre_pipeline -> tongan_pipeline_exec -> tongan_post_pipeline`.
The user flow remains TXT upload, create task, watch progress, and download
final video. Mock mode remains the default unless
`NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real`.

## Branch And Commit

- Branch: `feature/stage6c-marketing-video-three-node-contract`
- Base commit before Stage 6C work: `731db95`
- Stage 6C commit: `9dc3829`

## Changed Files

- `apps/web/lib/marketing-video.ts`
- `apps/web/components/marketing-video/workspace.tsx`
- `apps/web/lib/proxy-target.ts`
- `apps/web/app/api/proxy/[...path]/route.ts`
- `apps/web/tests/fixtures/stage5c-marketing-video.ts`
- `apps/web/tests/marketing-video-real-api.spec.ts`
- `docs/stage6c_marketing_video_three_node_contract_report.md`

## Stage 5C Fixture Source

Fixture data was based on:

- `/Users/malin13/Documents/trae_projects/website0430/docs/stage5c_remote_evidence/stage5c_sworker_handoff_e2e_result.json`
- Workflow: `wf_0963371cc1a241e488b475f92fbf3365`
- Final video key: `video-workflows/staging/tongan/wf_0963371cc1a241e488b475f92fbf3365/subtasks/tongan_post_pipeline/attempt-5/final/b_video.mp4`

The test fixture keeps the Stage 5C subtask shape and deliberately preserves
the evidence payload's non-canonical returned order, so the frontend adapter
must sort by known `node_code`.

## Contract Decisions

- Real-mode workflow detail is normalized in the frontend adapter before the UI
  consumes it.
- Known Stage 5C labels:
  - `tongan_pre_pipeline` -> `准备素材与基础视频`
  - `tongan_pipeline_exec` -> `智能匹配素材`
  - `tongan_post_pipeline` -> `渲染成片`
- Unknown future nodes fall back to API `node_name` or `node_code`.
- Failed or manual-required workflow messages include the failed subtask's
  human label when a failed subtask exists.
- `download.available` is treated as true when `final_video_url` exists, so a
  final video URL still exposes the download action.
- The proxy target selection helper keeps Marketing Video routed by
  `MARKETING_VIDEO_API_BASE_URL` while preserving Smart Cut and legacy routing.

## UI Behavior Changed

- Real-mode node cards show the three Stage 5C human labels in canonical order.
- Special-node failures show `智能匹配素材：<error>` instead of only a vague
  workflow-level failure.
- Worker kind is no longer printed in the node-card metadata; the UI keeps
  node code and attempt for debugging without exposing worker routing as a user
  concept.
- Empty node-progress copy now names the three TONGAN stages.

## Tests Run

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
npm run build
```

PASS. Next.js production build and type checks passed.

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
npm run test:e2e -- marketing-video.spec.ts
```

PASS. Mock-mode regression: `1 passed`.

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
```

PASS. Real-mode contract regression: `6 passed, 1 skipped`. The skipped test is
the opt-in live Stage 5C smoke.

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend
git diff --check
```

PASS.

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
npm run lint
```

Not run successfully: this package still has no `lint` script.

## Pass / Fail

PASS.

Required checks covered:

- Mock mode still works.
- Real-mode adapter parses a Stage 5C succeeded payload.
- Real-mode adapter parses a Stage 5C failed special-node payload.
- UI shows the three human labels.
- UI shows failure at `智能匹配素材` when `tongan_pipeline_exec` fails.
- UI exposes final download when `final_video_url` exists.
- Proxy target selection routes Marketing Video through
  `MARKETING_VIDEO_API_BASE_URL`.
- Smart Cut proxy target selection remains separate.

## Screenshots

No screenshots captured. The layout was not redesigned; changes were limited to
copy, labels, metadata, and contract behavior.

## Known Gaps

- Same-origin browser TOS PUT from B staging or the formal frontend origin still
  needs final RC validation. This task does not prove browser TOS CORS from that
  origin.
- The live Stage 5C smoke remains opt-in and was not run by default.
- No lint script exists in `apps/web/package.json`.

## Spec Deviations

None.

## Handoff Notes

- Do not collapse these labels back to `tongan_legacy_run`; Stage 5C is the
  valid TONGAN route.
- If future backend nodes are added, keep unknown-node fallback behavior instead
  of making the adapter crash.
