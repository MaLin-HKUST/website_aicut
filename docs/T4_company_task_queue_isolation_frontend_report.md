# T4 Company Task Queue Isolation Frontend Report

## Summary

Hardened the frontend proxy and task-center UI so user-mode task requests are scoped to the authenticated user's company. The proxy strips client-supplied `X-AICUT-*` spoofing headers, fetches `/auth/me`, injects trusted context headers into user API calls, and normalizes user-mode legacy `company_id` query/body values.

The `/tasks` UI now defensively filters shared task-center rows, Smart Cut summaries, Marketing Video summaries, detail loads, and sidebar preview tasks to the logged-in company.

## Changed Files

- `apps/web/app/api/proxy/[...path]/route.ts`
- `apps/web/components/marketing-video/workspace.tsx`
- `apps/web/components/navigation/use-user-workspace-data.ts`
- `apps/web/components/task-center/task-center-shell.tsx`
- `apps/web/components/task-center/user-tasks-shell.tsx`
- `apps/web/lib/marketing-video.ts`
- `apps/web/lib/smart-cut.ts`
- `apps/web/lib/task-center.ts`
- `apps/web/tests/fixtures/stage5c-marketing-video.ts`
- `apps/web/tests/marketing-video-real-api.spec.ts`

## Contract Decisions

- `/api/proxy/auth/me` remains the trusted browser-visible source of `company_id`.
- User-mode `/api/proxy/api/*` requests receive `X-AICUT-User-Id`, `X-AICUT-Company-Id`, and `X-AICUT-Role` from the proxy, not from the browser.
- User-mode task-center and Smart Cut list queries force `company_id` to the authenticated company.
- Marketing Video upload/create sends the authenticated `company_id` instead of the old `"tongan"` company placeholder.
- Same-company mixed task types remain visible in one queue; cross-company rows are dropped defensively.

## Tests Run

```bash
npm run build
# passed
```

```bash
npm run test:e2e -- marketing-video.spec.ts
# 7 passed (47.4s)
```

```bash
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
# 10 passed, 1 skipped (31.9s)
```

```bash
git diff --check
# passed
```

## Pass / Fail

PASS_WITH_CONDITIONS

Frontend local validation passed. B staging browser validation was not performed in this implementation pass.

## Known Gaps

- Legacy Smart Cut backend enforcement was not changed in this frontend worktree.
- `apps/web/test-results/` remains an existing untracked Playwright output directory and was not included.

## Spec Deviations

None.

## Handoff Notes

- Production touched: no.
- Next recommended step: build a frontend artifact from this branch and validate `/tasks`, `/marketing-video`, `/smart-cut`, and `/login` on B/RC before production promote.
