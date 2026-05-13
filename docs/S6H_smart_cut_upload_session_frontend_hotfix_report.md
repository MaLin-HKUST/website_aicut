# S6H Smart Cut Upload Session Frontend Hotfix Report

## Summary

Decision: PASS_WITH_CONDITIONS.

The production Smart Cut frontend runtime was rebuilt and promoted with a fixed upload client. The promoted bundle sends `upload_session_id` and `uploaded_keys` to `upload-complete`, renders object-shaped API errors as readable text, and uses Next.js 15.5.18 to clear the production Next high advisories that blocked release.

## Changed Files

- `apps/web/lib/smart-cut.ts`
- `apps/web/package.json`
- `apps/web/package-lock.json`
- `docs/S6H_smart_cut_upload_session_frontend_hotfix_report.md`

## Contract Decisions

- `uploadDirectInputs()` now preserves `uploaded_keys` and also sends `upload_session_id`.
- Object API errors are reduced through `message`, `detail`, and `error` before falling back to JSON text.
- Existing production Smart Cut component exports were reconciled in the same client file: `startAnalyze`, `reconcileUpload`, and `updateSmartCutTaskTitle`.
- Next.js was pinned to `15.5.18` because `npm audit --omit=dev` flagged production `next@15.5.15` high advisories.

## Tests Run

- `npm run build` -> pass.
- `npm run test:e2e -- smart-cut*.spec.ts || true` -> no matching spec files.
- `npm run test:e2e -- marketing-video.spec.ts || true` -> no matching spec files.
- `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts || true` -> no matching spec files.
- `git diff --check` -> pass.
- Production source local build from A source copy -> pass, standalone generated.
- Production route smoke `/login`, `/tasks`, `/smart-cut` -> pass.
- Smart Cut browser upload smoke -> pass; new task `5a843ca4-bf13-43f7-b196-c4acfcffada7` reached `analyzing`.

## Pass / Fail

PASS_WITH_CONDITIONS.

## Known Gaps

- Production A itself killed `next build` during trace collection, so the archive was built locally from the synchronized production source copy and then promoted on A.
- `npm audit --omit=dev` still reports high findings for dev-only Playwright and moderate PostCSS via Next; production Next high findings were cleared by `15.5.18`.

## Spec Deviations

None.

## Handoff Notes

Rollback command:

```bash
ssh malin@14.103.249.104 'bash /home/malin/release_0425/website_aicut/scripts/release_0425/rollback_web_3301_last_promotion.sh'
```
