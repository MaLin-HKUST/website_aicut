# Stage 7A RC Integration And Same-Origin Browser Upload Report

## Summary

BLOCKED at Gate 7A.1.

The no-bridge Browser TOS PUT harness was implemented, but the live validation
could not obtain a fresh Stage 5C presigned PUT URL because B staging API access
became unavailable during the run. No browser TOS PUT was attempted, no
workflow was created, and no final mp4 was downloaded.

## Candidate Versions

- frontend commit: `66617bf5219ae27c7f5961ce9e65133fec66d29a`
- frontend branch: `rc/stage7a-marketing-video-staging-validation`
- website0430 commit: `4d7c58d1e50377b578170c843442ff6fcc4cd52f`
- website0430 state: dirty Stage 5C source tree; Stage 5C.7 evidence exists but
  local `HEAD` remains the Stage 5B report commit.
- aicut2602 commit: `7f9446c020200d43869cccb0082347c2a52676c6`
- aicut2602 state: dirty `feature/stage5c-tongan-pipeline-bundle` worktree.

## Deployment Topology

- B API URL intended for Next server: `http://127.0.0.1:28080`, SSH tunnel to B
  staging `127.0.0.1:18080`.
- frontend origin planned for browser validation: `http://14.103.87.112:3007`.
- gworker endpoint: `http://14.103.212.96:8080`; local public access timed out,
  but an SSH-local worker health/version probe passed earlier in the run.
- sworker endpoint: `ssh malin@49.51.193.177`, local
  `http://127.0.0.1:8081`; health/version probe passed earlier in the run.
- TOS endpoint type: browser presigned URLs use the public bucket domain
  `autocut-malin.tos-cn-shanghai.volces.com`.
- bridge used: no.
- Playwright route interception used: no.
- backend upload fallback used: no.

The runtime still has Stage 5C infrastructure conditions: sworker tunnel/proxy,
`CODEX_SANDBOX_MODE=danger-full-access`, and source-mounted/proof-only runtime.
Even if functional validation passes later, the highest allowed result remains
`PASS WITH CONDITIONS` until these are removed.

## Gate 7A.1 Browser TOS PUT Micro Test

Result: BLOCKED before presign.

Observed during execution:

- B staging ping succeeded.
- TCP connect to `14.103.87.112:22` succeeded, but SSH timed out during banner
  exchange.
- Public `14.103.87.112:18080` timed out from local.
- Existing local tunnel `127.0.0.1:28080 -> B 127.0.0.1:18080` timed out on
  `/health`.
- After closing stale local tunnels, delayed SSH retry still timed out during
  banner exchange.

Because no fresh Stage 5C presigned PUT URL could be obtained, the browser micro
PUT was not attempted. This preserves the hard gate ordering and avoids a false
PASS.

## Full Workflow Result

Not run.

Per the hard gate order, full workflow validation must wait until Gate 7A.1
passes. No workflow was created.

## Final Video Validation

Not run.

No final mp4 was available because no workflow was created. Required validation
still remains:

- download final mp4 to an untracked temp directory
- `ffprobe` duration > 0, `1080x1920`, `30fps`, `h264/aac`
- compare duration/format/contact sheet with Stage 5C.7 golden
- record human quick-watch conclusion

## Tests Run

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
npm run build
```

Result: PASS.

```bash
npm run test:e2e -- marketing-video.spec.ts
```

Result: PASS, `1 passed`.

```bash
NEXT_PUBLIC_MARKETING_VIDEO_API_MODE=real npm run test:e2e -- marketing-video-real-api.spec.ts
```

Result: PASS, `6 passed, 1 skipped`. The skipped test is the opt-in bridged
Stage 6C live smoke and was intentionally not used for Stage 7A evidence.

```bash
npm run test:e2e -- stage7a-rc-validation.spec.ts --list
```

Result: PASS. Playwright listed the three Stage 7A live RC tests.

Remote/runtime probes attempted:

```bash
curl -fsS --max-time 5 http://14.103.87.112:18080/health
curl -fsS --max-time 5 http://14.103.212.96:8080/worker/health
ssh malin@14.103.87.112 'curl -fsS --max-time 5 http://127.0.0.1:18080/health'
ssh malin@14.103.212.96 'curl -fsS --max-time 5 http://127.0.0.1:8080/worker/health'
ssh malin@49.51.193.177 'curl -fsS --max-time 5 http://127.0.0.1:8081/worker/health'
```

Results:

- B public API: timeout.
- gworker public API: timeout.
- B SSH probe: initially passed, later SSH banner timed out and tunnel could not
  be restored.
- gworker SSH-local health/version: passed.
- sworker SSH-local health/version: passed.

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend
git diff --check
```

Result: PASS.

## Evidence Files

- `docs/stage7a_remote_evidence/stage7a_runtime_versions.json`
- `docs/stage7a_remote_evidence/stage7a_browser_origin.txt`
- `docs/stage7a_remote_evidence/stage7a_micro_presign_response_redacted.json`
- `docs/stage7a_remote_evidence/stage7a_micro_tos_put_network_summary.json`
- `docs/stage7a_remote_evidence/stage7a_create_workflow_response.json`
- `docs/stage7a_remote_evidence/stage7a_polling_summary.json`
- `docs/stage7a_remote_evidence/stage7a_download_response_redacted.json`
- `docs/stage7a_remote_evidence/stage7a_ffprobe_summary.json`
- `docs/stage7a_remote_evidence/stage7a_golden_comparison_summary.json`
- `docs/stage7a_remote_evidence/stage7a_rc_result.json`

## Pass / Fail

BLOCKED.

Blocked gate: Gate 7A.1 Browser TOS PUT micro test.

Smallest next action: restore a reachable B staging API path, preferably
`127.0.0.1:28080 -> B 127.0.0.1:18080`, then rerun:

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut_worktrees/stage6a-marketing-video-frontend/apps/web
PLAYWRIGHT_SKIP_WEBSERVER=1 \
PLAYWRIGHT_BASE_URL=http://14.103.87.112:3007 \
PLAYWRIGHT_CHROMIUM_ARGS='--host-resolver-rules=MAP 14.103.87.112 127.0.0.1' \
RUN_STAGE7A_RC=1 \
STAGE7A_SAMPLE_TXT=/Volumes/XIAOMA-A-1T/Taskspace_Tongan/wenan/wuyi_txt_split_10_files/07.txt \
npm run test:e2e -- stage7a-rc-validation.spec.ts --workers=1
```

## Known Gaps

- Gate 7A.1 was not run because fresh presign was unreachable.
- Gate 7A.2 full workflow was not run.
- Gate 7A.3 final video validation was not run.
- Regression suite remains to be run after the live gate can execute.
- The local auth/task-center stub was prepared only to allow the Stage 6C page
  to load during RC validation; it was not used for any TOS upload or workflow
  API fallback.

## Spec Deviations

None.

## Handoff Notes For RC Release

Do not enter Stage 7B. Restore B staging SSH/API reachability first, then rerun
Gate 7A.1 with the no-bridge harness. If Gate 7A.1 passes, continue to full
workflow and required final video validation in the same RC branch.
