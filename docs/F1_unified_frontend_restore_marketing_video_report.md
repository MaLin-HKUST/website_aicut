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

- Local archive: `/tmp/F1-unified-frontend-real_web_runtime.tgz`
- Production archive: `/home/malin/preview_3302_slot/F1-unified-frontend-real_20260514_220835_web_runtime.tgz`
- SHA256: `4c422d9ac88dbb43c5552d6a5e195f41d870b285655c74a3e348a93d38fff726`
- Production promotion time: `20260514_220851`
- Production backup: `/home/malin/website_aicut_prod/backups/web_runtime/web_runtime_20260514_220851`
- Environment: built with `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real`.

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
- Runtime symbols include `生成营销视频`, Marketing Video API `Real`, and Smart Cut task rename logic (`修改名称`).
- `last_promotion_3301.env` records `MARKETING_VIDEO_API_BASE_URL=http://14.103.87.112:18080`.

## Rollback

Use the standard frontend rollback command if needed:

```bash
ssh aliyun 'bash /home/malin/release_0425/website_aicut/scripts/release_0425/rollback_web_3301_last_promotion.sh'
```

## Notes

The first F1 archive was built without `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real` and was immediately superseded before final signoff. The only accepted production artifact is the `F1-unified-frontend-real` archive listed above.

The A promotion script still exits with code `137` because its local curl smoke is killed on the host, but the runtime switch completes and the independent public route smoke passed. Future frontend releases should use one unified frontend integration source instead of separate S/T artifacts.
