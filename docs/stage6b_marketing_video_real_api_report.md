# Stage 6B Marketing Video Frontend Real API Report

## Summary

Connected the existing Stage 6A `/marketing-video` page to the verified Stage 5B TONGAN API contract without redesigning the page or adding a second proxy. Mock mode remains the default. Real mode now parses the nested Stage 5B presign response, uploads with the returned `PUT` method using the same browser-direct TOS pattern as Smart Cut, submits `tos_key=objects[0].upload_key`, handles Stage 5B nested errors, and accepts `final_video_url` from the download endpoint.

The existing generic proxy was kept. A small compatibility fix buffers JSON request bodies before forwarding them, while preserving streaming behavior for multipart and large non-JSON requests. This was required because Stage 5B received an empty streamed JSON body from the proxy during live workflow creation. The proxy now also supports `MARKETING_VIDEO_API_BASE_URL` for `/api/proxy/api/marketing-video/...` so Marketing Video and Smart Cut can target different backend services without creating a second proxy.

## Changed Files

- `apps/web/lib/marketing-video.ts`
- `apps/web/app/api/proxy/[...path]/route.ts`
- `apps/web/tests/marketing-video-real-api.spec.ts`
- `docs/stage6b_marketing_video_real_api_report.md`

## Contract Decisions

- Mock mode remains active unless `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real`.
- Real presign sends `customer_id=tongan`, `company_id=tongan`, `task_type=std_marketing_video`, `workflow_name=TONGAN`, `mode=standard`, `filename`, and `content_type`.
- Real upload reads `objects[0].upload_url`, `objects[0].upload_key`, and `objects[0].method`; flat Stage 6A fallback fields are still tolerated.
- Marketing Video keeps the Smart Cut-style browser upload architecture: `XMLHttpRequest`, presigned URL `PUT`, and only the `Content-Type` request header. If upload fails for one TOS prefix/origin but Smart Cut works, investigate backend signing parameters, TOS key prefix, and bucket CORS before changing frontend upload architecture.
- API errors are surfaced from `error.message`, then `detail`, then `message`.
- No page redesign, new UI dependency, RBZJ/KDT enablement, Smart Cut rewrite, backend change, or production touch was introduced.

## Real API Configuration

Mock/default:

```bash
npm run dev
```

Real mode through existing proxy:

```bash
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real \
MARKETING_VIDEO_API_BASE_URL=http://127.0.0.1:28080 \
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Fallback for older local setups remains `INTERNAL_API_BASE_URL`, but `MARKETING_VIDEO_API_BASE_URL` is preferred for Stage 6B so Smart Cut and Marketing Video do not share an accidental target.

The local B-staging tunnel check found:

```bash
curl -fsS --max-time 3 http://127.0.0.1:18080/health
# failed locally: no listener

curl -fsS --max-time 3 http://127.0.0.1:28080/health
# {"environment":"staging","ok":true,"service":"marketing-video-api","stage":"5B"}
```

## Tests Run

```bash
npm run build
```

Pass. Next.js production build and TypeScript validity check passed.

```bash
npm run test:e2e -- marketing-video.spec.ts
```

Pass. Existing Stage 6A mock regression passed: `1 passed`.

```bash
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real \
npm run test:e2e -- marketing-video-real-api.spec.ts
```

Pass. Real-mode browser contract tests passed: `2 passed, 1 skipped`. The skipped test is the opt-in live Stage 5B smoke.

```bash
PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 \
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real \
MARKETING_VIDEO_API_BASE_URL=http://127.0.0.1:28080 \
RUN_STAGE6B_LIVE_SMOKE=1 \
npx playwright test marketing-video-real-api.spec.ts -g "live Stage 5B" --workers=1
```

Pass. Created a real Stage 5B workflow through the existing proxy and polled detail once:

```md
workflow_id: wf_7602b4dcba714bc1af75ca3420f0b5c1
```

## Browser Evidence

- Mock browser regression: `/marketing-video` selected TXT, created mock TONGAN task, displayed node progress, failure state, success state, and download button.
- Real-mode contract browser test: verified `Real` indicator, nested presign parsing, browser `PUT`, create payload `tos_key`, detail polling, nested `{ error: { message } }` display, and `/download` `final_video_url`.
- Live Stage 5B smoke: existing proxy reached B staging via `MARKETING_VIDEO_API_BASE_URL=http://127.0.0.1:28080`, created `wf_7602b4dcba714bc1af75ca3420f0b5c1`, and fetched workflow detail.

Note: direct browser PUT to the real TOS presigned URL from localhost initially failed with `上传到 TOS 失败，请检查网络后重试。`. This does not prove the deployed frontend origin will fail, because Smart Cut already uses the same browser-direct TOS pattern and the bucket may allow the production/staging website origin rather than localhost. The opt-in live smoke uses a Playwright-only TOS PUT bridge so the real Stage 5B presign/create/detail path can be verified while keeping the production code on direct presigned `PUT`.

## Pass / Fail

PASS WITH CONDITIONS.

- Gate 6B.1 Contract Adapter Ready: PASS.
- Gate 6B.2 Proxy Real Mode Ready: PASS. The existing proxy is reused; JSON forwarding was fixed in place, and Marketing Video can use `MARKETING_VIDEO_API_BASE_URL`.
- Gate 6B.3 Browser Real API Smoke Ready: PASS WITH CONDITIONS because the live workflow create/detail path passed, but localhost direct browser TOS PUT needed a test harness bridge.
- Gate 6B.4 Frontend Ready For RC: PASS WITH CONDITIONS pending same-origin B staging or formal frontend-origin TOS PUT confirmation.

## Known Gaps

- Full wait-to-succeeded/download was not run in the live browser smoke to avoid a long generation wait.
- TOS CORS/signature behavior for direct browser PUT from the B staging or formal frontend origin still needs confirmation. The frontend remains implemented against the same direct presigned `PUT` contract used by Smart Cut.
- The requested worktree file `/Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/AGENTS.md` was not present during this thread.

## Spec Deviations

None

## Handoff Notes

- Keep using `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real` plus `MARKETING_VIDEO_API_BASE_URL` for staging validation.
- Do not add a separate marketing-video proxy unless a future backend route requires behavior that the existing `/api/proxy/api/...` route cannot support.
- RC validation should open `/marketing-video` from B staging or the formal frontend origin, upload a TXT in a real browser, and confirm the TOS `PUT` succeeds from that origin.
- If same-origin browser testing still reports upload failure, configure/verify backend signing parameters, TOS key prefix, and bucket CORS before changing frontend upload architecture.
