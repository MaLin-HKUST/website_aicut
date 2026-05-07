# Stage 6A Marketing Video Frontend Report

## Summary

Implemented the first user-facing `/marketing-video` shell for TONGAN standard marketing video creation in the existing `website_aicut` frontend. The page uses the current `UserWorkspaceShell`, existing `Button` / `Card` / `Input` components, mock-first Stage 5A client behavior, TXT selection, create flow, status panel, subtasks list, failure state, and success/download state.

## Changed Files

- `apps/web/app/marketing-video/page.tsx`
- `apps/web/components/marketing-video/workspace.tsx`
- `apps/web/lib/marketing-video.ts`
- `apps/web/components/navigation/user-workspace-shell.tsx`
- `apps/web/components/navigation/use-user-workspace-data.ts`
- `apps/web/app/welcome/page.tsx`
- `apps/web/lib/task-center.ts`
- `apps/web/components/task-center/user-tasks-shell.tsx`
- `apps/web/tests/marketing-video.spec.ts`
- `docs/stage6a_marketing_video_frontend_report.md`

## Visual Consistency Decisions

- Reused the existing user workspace frame, side navigation, metric header, warm neutral panels, rounded controls, and task-center card rhythm.
- Added `生成营销视频` as a first-class workspace nav item and welcome entry without removing or renaming Smart Cut.
- Kept the page operational and compact: no marketing hero, no gradients, no decorative blobs, no new UI dependency.
- Added responsive protection to the shared workspace shell so long account names wrap inside metric boxes and the shell stacks on mobile.

## API Contract Used

Stage 5A contract file was not present at `website0430/docs/stage5a_marketing_video_api_contract.md`, so Stage 6A used the provisional Stage 5A contract embedded in the thread prompt.

Public proxy endpoints represented in `apps/web/lib/marketing-video.ts`:

- `POST /api/proxy/api/marketing-video/uploads/presign`
- `POST /api/proxy/api/marketing-video/workflows`
- `GET /api/proxy/api/marketing-video/workflows/{workflow_id}`
- `GET /api/proxy/api/marketing-video/workflows/{workflow_id}/download`
- `POST /api/proxy/api/marketing-video/workflows/{workflow_id}/cancel`

## Mock Mode Behavior

`NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real` switches the client to real proxy calls. Any other value, including an unset variable, uses mock mode because no real Stage 5A frontend API base is configured in this repo yet.

Mock mode validates a non-empty `.txt` file, simulates upload progress, creates a TONGAN workflow, stores mock workflow state in `localStorage`, advances status on polling, and exposes success/failure example buttons so Stage 6A can verify terminal UI states before the backend is connected.

## Tests Run

- `npm ci`
  - Pass. Installed existing lockfile dependencies.
- `npm run lint -- --no-cache || npm run lint`
  - Fail by project configuration: `package.json` has no `lint` script.
- `npm run build`
  - Pass. `/marketing-video` built as a static app route and TypeScript validity check passed.
- `npm run test:e2e -- marketing-video.spec.ts`
  - Pass. Verified mock route render, TXT selection, create task, node list, failure state, success state, and download button.

Note: one earlier `npm run build` retry failed with `Cannot find module for page: /_document` because it was run concurrently with the Playwright dev server and both wrote `.next`. The sequential rerun passed.

## Screenshots / Manual Verification

- Desktop screenshot: `/tmp/stage6a-marketing-video-desktop.png`
- Mobile screenshot: `/tmp/stage6a-marketing-video-mobile.png`

Manual screenshot review checked:

- `/marketing-video` renders inside the existing workspace shell.
- Desktop layout matches the current warm neutral workspace style.
- Mobile width stacks without overlapping text.
- Mock create workflow works.
- Success state shows download action.
- Failure state shows a user-readable error.

## Pass / Fail

Pass with one repo-level caveat: the web package has no lint script, so lint could not be run. Build and focused Playwright verification passed.

## Known Gaps

- Real Stage 5A presign response field names may need a small adapter adjustment after `stage5a_marketing_video_api_contract.md` exists.
- Full task-center listing for marketing-video tasks depends on Stage 5A adding those tasks to `/api/task-center/tasks`.
- Events stream UI is not implemented; the page currently uses workflow detail polling and subtasks from the aggregate detail response.

## Spec Deviations

None

## Handoff Notes For Stage 6B

- Connect `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real` after Stage 5A is deployed behind the existing `/api/proxy` route.
- Confirm the exact presign response shape and update `MarketingVideoPresignResponse` if Stage 5A uses different field names.
- Once task center API returns `task_type: "std_marketing_video"`, `/tasks` will display the marketing-video type label, status, failure reason, summaries, and download link. A deeper detail drawer can be added if Stage 5A exposes workflow detail by task-center id.
- Add events timeline support from `/api/proxy/api/marketing-video/workflows/{workflow_id}/events` when the backend event payload is stable.

