# 0415 Acceptance - Playwright Smart Cut E2E

## Scope
- Feature: `A04`
- Execution host: `14.103.249.104`
- Target: `https://xiaomajianji.cn`

## What Was Verified
- Browser-authenticated user flow reached `/welcome`
- Browser-authenticated flow reached `/smart-cut/{taskId}`
- Analyze completed and the task page hydrated into the preview editor state
- Browser clicked `生成试听`
- Browser clicked `生成视频`
- Browser landed in `/tasks?taskId=...`
- Task center rendered the created task

## Deployment Fix Included In This Verification
- The deployed 0415 Next runtime on A-machine had been missing `/.next/static`
- This caused repeated `404` on `/_next/static/*` and prevented client hydration
- The runtime package was rebuilt to include:
  - `server.js`
  - `/.next/static`
- The A-machine web slot on `3001` was restarted with the corrected runtime

## Command
```bash
ssh malin@14.103.249.104 \
  "cd /home/malin/release_0415_slot/src_af30ae1/apps/web && \
   PLAYWRIGHT_BASE_URL=https://xiaomajianji.cn \
   PLAYWRIGHT_SKIP_WEBSERVER=1 \
   npx playwright test tests/rel0415-smart-cut-live.spec.ts --config playwright.config.ts"
```

## Result
- `1 passed (27.3s)`

## Verdict
- `A04 PASS`
