# 0415 Acceptance Playwright Live Routes

## Date
- 2026-04-17

## Execution Host
- A-machine: `14.103.249.104`

## Command
```bash
cd /home/malin/release_0415_slot/src_af30ae1/apps/web
PLAYWRIGHT_BASE_URL=https://xiaomajianji.cn \
PLAYWRIGHT_SKIP_WEBSERVER=1 \
npx playwright test tests/rel0415-live-routes.spec.ts --config playwright.config.ts
```

## Result
- `5 passed (2.2s)`

## Covered Routes
- `/welcome`
- `/smart-cut`
- `/tasks`
- `/tts`
- `/admin/tasks`

## Notes
- The suite had to run on A-machine because the current local environment cannot resolve `xiaomajianji.cn`.
- Assertions for `/tasks`, `/admin/tasks`, and `/tts` were tightened to the actual rendered route markers in the live HTML output.
