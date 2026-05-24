# K7A KDT TTS Voice Selection Frontend Report

## Summary

Decision: `BLOCKED` for full K7A because staging artifact/E2E is blocked outside the frontend. Frontend local implementation and tests passed.

Update: the standalone `/tts` page now also exposes the same approved voice selector and sends the selected voice as `voice_name` to `/api/proxy/user/tts/generate`.

## Changed Files

- `apps/web/lib/marketing-video.ts`
- `apps/web/lib/tts-voices.ts`
- `apps/web/app/tts/page.tsx`
- `apps/web/components/marketing-video/workspace.tsx`
- `apps/web/tests/admin-flow.spec.ts`
- `apps/web/tests/tts.spec.ts`
- `apps/web/tests/marketing-video.spec.ts`
- `apps/web/tests/marketing-video-real-api.spec.ts`
- `docs/K7A_kdt_tts_voice_selection_frontend_report.md`

## Contract Decisions

- `KDT_TTS_VOICES` exports exactly `康迪`, `日标住建-小唐`, and `日标住建-凯迪`.
- The standalone `/tts` page uses the same allowlist, defaults to `康迪`, and sends `voice_name`.
- The dropdown appears only for `profile.kind === "kdt"`.
- Default selected value is `康迪`.
- KDT create requests include top-level `tts_voice`.
- TONGAN users do not see the control and do not send `tts_voice`.

## Tests Run

```text
npm run build -> pass
npm run test:e2e -- tts.spec.ts -> 1 passed
npm run test:e2e -- marketing-video.spec.ts --workers=1 -> 7 passed
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts -> 11 passed, 1 skipped
git diff --check -> pass
```

An initial parallel Playwright run of `marketing-video.spec.ts` failed because another test server already held `127.0.0.1:3000`; a later default-worker run hit 30s timeouts in three non-KDT scenarios, and the same suite passed with `--workers=1`. A later `admin-flow.spec.ts` run failed before reaching `/tts` because the local legacy backend on `127.0.0.1:8000` was not running, so `/tts` behavior is covered by `tts.spec.ts` with mocked auth and generation routes.

## Pass / Fail

```text
frontend dropdown: PASS
standalone /tts selected voice payload: PASS
TONGAN hidden/no-send behavior: PASS
KDT selected voice payload: PASS
production promote: not run, out of scope
```

## Known Gaps

- No production frontend artifact was built or promoted.

## Spec Deviations

None.

## Handoff Notes

Frontend is ready for K7A artifact integration after backend/aicut source transport is unblocked.
