# K6C KDT Unified Frontend Domain Beta Report

## Decision

`PASS_WITH_CONDITIONS`

K6C exposed KDT through the unified production `/marketing-video` page and proved the browser/API/worker route end to end for company 1. The condition is material: the current KDT backend/runtime still returns the same 3 second black/silent placeholder video that K6B produced, even when custom opener and ending videos are uploaded. This means the domain beta wiring is live, but KDT output quality is not customer-ready.

## Scope

- Production A frontend was promoted from a clean exact commit artifact.
- B K6B API, gworker KDT runtime, and sworker KDT runtime were reused.
- Smart Cut, worker1, TONGAN algorithm runtime, B API code, and KDT worker code were not changed.

## Source And Artifact

- Frontend branch: `feature/K6C-kdt-unified-frontend-domain-beta`
- Source commits:
  - `6435d78` expose KDT through the unified marketing video page
  - `fe157d9` keep the K6C frontend inside the audit gate
- Production archive: `/home/malin/preview_3302_slot/K6C-kdt-unified-frontend-domain-beta-20260516-0218-r2_web_runtime.tgz`
- Archive sha256: `853635f321f408d0187c88b0107640de08f8254605ac8c36596a5015c1b6d66d`
- Production backup: `/home/malin/website_aicut_prod/backups/web_runtime/web_runtime_20260516_020107`
- Rollback:

```bash
ssh aliyun 'bash /home/malin/release_0425/website_aicut/scripts/release_0425/rollback_web_3301_last_promotion.sh'
```

The first archive was rebuilt because `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real` is a client build-time variable. The final promoted archive is the `r2` build with real mode baked in.

## Validation

Local frontend:

- `npm run build`: pass
- `npm run test:e2e -- marketing-video.spec.ts`: `7 passed`
- `NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts`: `11 passed, 1 skipped`
- `git diff --check`: pass
- `npm audit --omit=dev`: `0 high`, `0 critical`, `2 moderate`

Production route smoke:

- `/login`: 200
- `/tasks`: 200
- `/smart-cut`: 200
- `/marketing-video`: 200

Company 1 KDT browser proof:

- Login: `rbzj`
- Page mode: `KDT IP营销视频`, `API=Real`
- Browser direct TOS PUT without bridge/interception/fallback: pass
- Workflow without custom opener/ending: `wf_6eb07f744f324ebe8a631d8b75a3844d`, succeeded
- Workflow with custom opener/ending: `wf_da40308789ef4382b2b56a67304ed647`, succeeded
- Route:
  - `kdt_validate_inputs -> gworker-2-kdt-general`
  - `kdt_pre_pipeline -> gworker-2-kdt-general`
  - `kdt_pipeline_exec -> sworker-1-kdt-special`
  - `kdt_post_pipeline -> gworker-2-kdt-general`

Company 10 TONGAN non-regression:

- Login: `tongan1`
- Page mode: `TONGAN 标准`, `API=Real`
- KDT controls are not shown.
- Page is not locked.

## Final Media Result

Custom opener/ending workflow:

- Workflow: `wf_da40308789ef4382b2b56a67304ed647`
- Final key: `video-workflows/staging/kdt/wf_da40308789ef4382b2b56a67304ed647/final/a_video.mp4`
- SHA256: `bfb454df4d94345e94450ef5ed3b80f1b524cde623b63ab92ca14e2f4f31b062`
- ffprobe duration: `3.000000`
- Resolution: `1080x1920`
- Video codec: `h264`
- Audio codec: `aac`
- Audio volume: `mean_volume -91.0 dB`
- Visual check: black frames

This SHA256 is identical to the K6B final output. The KDT workflow is technically completing, but the generated media remains a placeholder/black output. This is not a K6C frontend regression; it is a backend/runtime quality gap carried forward from K6B.

## Evidence

- Evidence dir: `docs/K6C_kdt_unified_frontend_domain_beta_evidence/`
- Release manifest: `docs/K6C_kdt_unified_frontend_domain_beta_evidence/K6C_release_manifest.json`
- Browser create proof: `K6C_browser_create_custom_open_end_result.json`
- Route proof: `K6C_route_db_custom_open_end.json`
- ffprobe: `K6C_custom_open_end_ffprobe.json`
- Contact sheet: `K6C_custom_open_end_contact.jpg`
- Company 10 smoke: `K6C_company10_tongan_smoke.json`

No signed URL or MP4 is committed.

## Remaining Risks

- KDT output quality is blocked on backend/algorithm runtime: final media is black and silent.
- `npm audit --omit=dev` still reports two moderate advisories through Next/PostCSS metadata, but no high or critical findings.
- KDT is live as a controlled beta entry for company 1, not a customer-ready production workflow.

## Next Step

Open K6D as a backend/algorithm task: replace the KDT placeholder finalization path with the real rendered B-video output and require non-black visual/audio validation before declaring KDT customer-ready.
