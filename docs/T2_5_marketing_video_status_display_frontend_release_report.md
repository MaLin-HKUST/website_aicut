# T2.5 Marketing Video Status Display Frontend Release Report

## Summary

Released the T2 frontend task-center display changes to B staging and the
customer domain.

Decision: `PASS_WITH_CONDITIONS`

## Changed Files

- `apps/web/lib/marketing-video.ts`
- `apps/web/components/task-center/user-tasks-shell.tsx`
- `apps/web/tests/marketing-video-real-api.spec.ts`
- `docs/T2_marketing_video_task_status_display_frontend_report.md`
- `docs/T2_5_marketing_video_status_display_frontend_release_report.md`

## Contract Decisions

- `/tasks` uses backend `display_status` before falling back to subtask-derived state.
- Node rows render Chinese status and attempt text.
- Unknown backend node statuses render as `未知状态` rather than leaking raw strings.
- Production frontend keeps Marketing Video API routing to B.

## Tests Run

```text
npm ci
-> PASS, 0 vulnerabilities

npm run build
-> PASS

npm run test:e2e -- marketing-video.spec.ts
-> PASS, 7 passed

NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
-> PASS, 9 passed, 1 skipped

PLAYWRIGHT_SKIP_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://14.103.87.112:3007 npx playwright test t2-live-ui.tmp.spec.ts --project=chromium --workers=1 --timeout=120000
-> PASS, 1 passed

PLAYWRIGHT_SKIP_WEBSERVER=1 PLAYWRIGHT_BASE_URL=https://xiaomajianji.cn npx playwright test t2-prod-ui.tmp.spec.ts --project=chromium --workers=1 --timeout=120000
-> PASS, 1 passed

git diff --check
-> PASS
```

## Pass / Fail

`PASS_WITH_CONDITIONS`

## Known Gaps

- Production A source build was killed during Next trace collection. Production
  promoted the same standalone runtime tar used to build and validate the B
  frontend image.
- Live browser checks mock auth and unrelated Smart Cut/shared task-center list
  routes, but use the real Marketing Video list/detail APIs.

## Spec Deviations

None.

## Handoff Notes

Production frontend artifact:

```text
/home/malin/preview_3302_slot/t2-status-display-20260512-d3920a4_web_runtime.tgz
sha256: f4d1c5adc29108f2d81544ab515f2c5bb6f34e270a0856ad9382d1db4b8a8a90
```

Production rollback:

```bash
ssh aliyun 'bash /home/malin/release_0425/website_aicut/scripts/release_0425/rollback_web_3301_last_promotion.sh'
```

