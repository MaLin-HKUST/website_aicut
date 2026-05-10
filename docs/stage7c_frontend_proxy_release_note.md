# Stage 7C Frontend Proxy Release Note

## Summary

Stage 7B browser validation found that forwarding upstream response framing
headers through the Next.js proxy could truncate `/api/proxy/auth/me` JSON in
the staging browser path.

The proxy now copies upstream response headers and removes unsafe hop/body
framing headers before returning the streamed response:

- `content-length`
- `content-encoding`
- `transfer-encoding`
- `connection`

## Changed Files

- `apps/web/app/api/proxy/[...path]/route.ts`
- `docs/stage7c_frontend_proxy_release_note.md`

## Contract Decisions

- The proxy preserves upstream status, status text, and safe headers.
- The proxy lets the Next.js runtime determine response framing for the returned
  body stream.
- This change is limited to the frontend proxy path and does not change
  workflow, TOS, worker, or production runtime configuration.

## Tests Run

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
npm run build
npm run test:e2e -- marketing-video.spec.ts
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
cd ..
git diff --check
```

## Pass / Fail

PASS.

- `npm run build`: PASS
- `npm run test:e2e -- marketing-video.spec.ts`: PASS, 1 passed
- `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts`: PASS, 6 passed and 1 live staging smoke skipped by test configuration
- `git diff --check`: PASS

## Known Gaps

- `apps/web/test-results/` is local Playwright output and is not part of this
  release note or commit.

## Spec Deviations

None.

## Handoff Notes

This release note reconciles the Stage 7B staging hot patch into source for
Gate 7C.0 before any sandbox hardening work.
