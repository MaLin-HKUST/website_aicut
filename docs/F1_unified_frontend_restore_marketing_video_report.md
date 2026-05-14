# F1 Unified Frontend Restore Marketing Video Report

Decision: `PASS`

Date: 2026-05-14

## Summary

Production A had been promoted with a Smart Cut-only frontend artifact:

`s6i-smart-cut-task-rename-action-20260513-2313_web_runtime.tgz`

That runtime did not include `/marketing-video`, so TONGAN/Marketing Video disappeared for company 10. F1 rebuilds a single frontend artifact from the current Smart Cut task-rename branch plus the Marketing Video route, navigation entry, proxy split, company gate, and task-center workflow detail logic.

## Scope

- Touched only the production A frontend runtime.
- Did not touch B API, gworker-2, sworker, worker1, Smart Cut backend, DB, or TOS data.
- Preserved Smart Cut task rename UI while restoring Marketing Video.

## Artifact

- Local archive: `/tmp/F1-unified-frontend-restore-marketing-video_web_runtime.tgz`
- Production archive: `/home/malin/preview_3302_slot/F1-unified-frontend-restore-marketing-video_20260514_220440_web_runtime.tgz`
- SHA256: `1e2ede3453b5fae6a72e4e6f5f86d6d6e89486910a9fbd27f0cdcf72c82d5b8c`
- Production promotion time: `20260514_220457`
- Production backup: `/home/malin/website_aicut_prod/backups/web_runtime/web_runtime_20260514_220457`

## Validation

Local:

- `npm run build`: pass, route list includes `/marketing-video`, `/tasks`, `/smart-cut`, `/login`.
- `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts`: `9 passed, 1 skipped`.
- `npm run test:e2e -- marketing-video.spec.ts`: `7 passed`.
- `git diff --check`: pass.

Production smoke:

- `https://xiaomajianji.cn/marketing-video`: `200`
- `https://xiaomajianji.cn/tasks`: `200`
- `https://xiaomajianji.cn/smart-cut`: `200`
- `https://xiaomajianji.cn/login`: `200`

Runtime proof:

- Current runtime route list includes `marketing-video/page.js`, `smart-cut/page.js`, `smart-cut/[taskId]/page.js`, `tasks/page.js`, and `login/page.js`.
- Runtime symbols include `生成营销视频` and Smart Cut task rename logic (`修改名称`).

## Rollback

Use the standard frontend rollback command if needed:

```bash
ssh aliyun 'bash /home/malin/release_0425/website_aicut/scripts/release_0425/rollback_web_3301_last_promotion.sh'
```

## Notes

The A promotion script still exits with code `137` because its local curl smoke is killed on the host, but the runtime switch completes and the independent public route smoke passed. Future frontend releases should use one unified frontend integration source instead of separate S/T artifacts.
