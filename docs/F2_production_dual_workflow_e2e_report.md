# F2 Production Dual Workflow E2E Report

## Decision

PASS_WITH_CONDITIONS

## Scope

- Production domain: `https://xiaomajianji.cn`
- Marketing Video account: `tongan1`, company `10`, 同安影视城
- Smart Cut account: `xyt1`, company `9`, 小樱桃文化
- Goal: prove both customer-facing workflows can be opened from the domain, run to completion, rename tasks, and remain company-isolated.

## Frontend Runtime

- Branch: `hotfix/F1-unified-frontend-restore-marketing-video`
- Previous commits:
  - `9c5201c` `Unify Smart Cut and Marketing Video frontend release paths`
  - `f8f635a` `Record the real-mode unified frontend promotion`
- Runtime archive promoted during this validation:
  - `/home/malin/preview_3302_slot/F2-unified-frontend-company-scope-real_20260514_2333_web_runtime.tgz`
  - sha256: `853ab1a8cb780f31c9b00e91a6964c6af2fb7d51df1a1e02e2a8bb91b973a738`
- Production backup created before promotion:
  - `/home/malin/website_aicut_prod/backups/web_runtime/web_runtime_20260514_233536`
- Route smoke after promotion:
  - `/login`: `200`
  - `/tasks`: `200`
  - `/smart-cut`: `200`
  - `/marketing-video`: `200`

## Frontend Fixes Applied

The unified frontend was missing the trusted company context required by the T4/T5 Marketing Video API path. The proxy now strips spoofable incoming `X-AICUT-*` headers and injects trusted values from the production auth session for `/api/proxy/api/marketing-video/...`.

Marketing Video create/upload now passes the authenticated numeric company id instead of the legacy string company id. This is required for company 10 to create and list its own workflows under the T4/T5 company isolation contract.

## Marketing Video E2E

- Account: `tongan1`
- Company: `10`, 同安影视城
- Workflow: `wf_5de3529c92f847ea99dad9fb93a7aa8b`
- Browser direct TOS PUT: `200`
- Create workflow: `201`
- Final status: `succeeded`
- Progress: `100`
- Route:
  - `tongan_pre_pipeline` -> `company10-marketing-general-1` -> `succeeded`
  - `tongan_pipeline_exec` -> `company10-marketing-special-1` -> `succeeded`
  - `tongan_post_pipeline` -> `company10-marketing-general-1` -> `succeeded`
- Final video TOS key:
  - `video-workflows/staging/tongan/wf_5de3529c92f847ea99dad9fb93a7aa8b/subtasks/tongan_post_pipeline/attempt-1/final/b_video.mp4`
- Local validation artifact:
  - `/tmp/f2_marketing_final2/wf_5de3529c92f847ea99dad9fb93a7aa8b_marketing_final.mp4`
- sha256:
  - `aead8dfffa5721c2daf07d374a6636897d132b1f177400093627f0cde61665fd`
- ffprobe:
  - duration: `27.921000`
  - size: `21839141`
  - video: `h264`, `1080x1920`, `30fps`
  - audio: `aac`
- Audio check:
  - mean volume: `-31.8 dB`
  - max volume: `-15.6 dB`
- Black frame check:
  - no `blackdetect` hit
- Contact sheet:
  - `/tmp/f2_marketing_final2/contact_sheet.jpg`
- Rename:
  - final title: `F2 同安 Marketing 验收已改名 2026-05-14T15:59:51`
  - result: `200`

## Smart Cut E2E

- Account: `xyt1`
- Company: `9`, 小樱桃文化
- Task: `b4d9e6f3-5eb7-4bc6-8760-dc9e9b7a07c9`
- Input video:
  - `/tmp/f2_smart_xingge4_60s.mp4`
  - derived from `/Volumes/XIAOMA-A-1T/XING_GE/4/4-数十亿银行理财彻底变天.mp4`
- Input text:
  - `/tmp/f2_smart_xingge4_60s.txt`
  - derived from `/Volumes/XIAOMA-A-1T/XING_GE/4/4-数十亿银行理财彻底变天.txt`
- Final status:
  - API status: `success`
  - current stage: `complete`
- Scheduler route:
  - `SMART_CUT_ANALYZE` -> `worker1-phase6` -> `SUCCESS`
  - `SMART_CUT_FINALIZE` -> `worker1-phase6` -> `SUCCESS`
- Final video TOS key:
  - `smart-cut/b4d9e6f3-5eb7-4bc6-8760-dc9e9b7a07c9/finalize/final_video.mp4`
- Subtitle TOS key:
  - `smart-cut/b4d9e6f3-5eb7-4bc6-8760-dc9e9b7a07c9/finalize/final_video.srt`
- Local validation dir:
  - `/tmp/f2_smartcut_e2e_xingge_r2_validate`
- sha256:
  - mp4: `cf4858950e069417730db5f80b06e876ea4a222b9071197fa4780d92e6c8f20f`
  - srt: `841fbb6d30987ffa6297f1796e05a0c09d43f273bedfcd777fd8bcf8dcd0200d`
- ffprobe:
  - duration: `44.360000`
  - size: `2738819`
  - video: `h264`, `1080x1920`, `25fps`
  - audio: `aac`
- Audio check:
  - mean volume: `-14.3 dB`
  - max volume: `-0.5 dB`
- Black frame check:
  - no `blackdetect` hit
- Contact sheet:
  - `/tmp/f2_smartcut_e2e_xingge_r2_validate/contact_sheet.jpg`
- Subtitle check:
  - generated SRT begins with the expected spoken text from the input sample.
- Rename:
  - final title: `F2 小樱桃 SmartCut 验收二次改名 2026-05-14T16:10:44Z`
  - result: `200`

## Worker1 Emergency Runtime Patches

The Smart Cut E2E exposed runtime-only worker1 failures. These were patched directly on worker1 under emergency pressure, with backups under `/data/worker_backups/`.

- `finalize_processor.py`: missing audio/pause cuts are optional instead of fatal.
- `run_worker_0425.sh`: exports `AICUT_PYTHON` to the worker virtualenv.
- `worker_0425.env`: added `DEEPSEEK_API_KEY`.
- `video_quality_control.py`: ffprobe bitrate probe failures return `None` instead of crashing.
- `finalize_processor.py`: disabled black/mock fallback on formal flow-b failure.
- `finalize_processor.py`: pause-cut generation exceptions now warn and continue without `--pause-cuts`.

Current worker1 process after restart:

- PID: `2386049`
- command: `/home/malin/website_aicut_worker_prod/.venv_worker/bin/python -m worker.main`

## Company Isolation

Marketing Video:

- `tongan1` / company 10 can list `wf_5de3529c92f847ea99dad9fb93a7aa8b`.
- `xyt1` / company 9 cannot list that workflow.
- `xyt1` detail request for the company 10 workflow returns `404 workflow_not_found`.

Smart Cut:

- `xyt1` / company 9 can list `b4d9e6f3-5eb7-4bc6-8760-dc9e9b7a07c9`.
- `tongan1` / company 10 task-center list contains no Smart Cut task from company 9.

## Queue And FCFS

Marketing Video:

- B API release: `t5s-auto-dispatcher-fcfs-20260513-1425`
- B API commit: `da080c3`
- Dispatcher timer: `marketing-video-dispatch-ready.timer`, active.
- Timer interval: 5 seconds.
- FCFS ordering from T5S: `workflow.created_at`, `subtask.created_at`, `workflow_id`, `subtask_id`.
- The F2 Marketing workflow moved through company-specific general/special workers and completed.

Smart Cut:

- A scheduler source orders pending scheduler tasks by `SchedulerTask.created_at.asc()`.
- The F2 Smart Cut task moved through analyze and finalize on `worker1-phase6` and completed.
- Current active scheduler rows show one old company 1 validation task still `PENDING`; it is unrelated to the company 9 E2E task.

Important distinction:

- Execution queues are FCFS by created time.
- The user-facing task list still displays rows ordered by updated time in current A API source. This means renaming can move a finished task in the visible list, but it does not change scheduler execution order. If the product requirement is also "display list sorted by created time", that needs a separate UI/API change.

## Time Display

- API timestamps are stored/returned as UTC-style timestamps.
- Browser validation with `Asia/Shanghai` locale displayed Beijing times in `/tasks`.
- Example:
  - Marketing created at `2026-05-14T15:36:35Z`, shown as `5/14 23:59` after rename/update.
  - Smart Cut created at `2026-05-14T16:04:24`, shown as `5/14 16:06` after rename/update on the current page.

The current UI label in the task card shows the "last updated" time, not necessarily the original created time. If the requirement is to show Beijing created time explicitly, this is a separate frontend task.

## Known Historical Residue

- One Smart Cut validation task from company 1 remains `PENDING`:
  - `24227bbe-7bf2-4bbd-83c6-e24655e263ce`
- B has old TONGAN validation rows in `ready` / `running` / `accepted` states from earlier stages.
- Some B `subtask_dispatch_attempts` for the successful F2 workflow still show `pending_push`, while the subtasks themselves are `succeeded`. This is historical T5/T6 bookkeeping debt and did not block the completed workflow.

## Conditions

This is `PASS_WITH_CONDITIONS` because:

- Worker1 Smart Cut fixes were emergency runtime patches, not yet reconciled into a clean source-controlled artifact.
- Smart Cut validation used a controlled XING_GE 60-second sample rather than a customer-provided full input.
- Old validation queue residue still exists and should be cleaned or archived in a separate maintenance task.
- The visible task list currently sorts by updated time, while execution queues are FCFS by created time.

## Rollback

Frontend rollback:

```bash
ssh aliyun 'bash /home/malin/release_0425/website_aicut/scripts/release_0425/rollback_web_3301_last_promotion.sh'
```

Worker1 rollback is file-specific using backups under `/data/worker_backups/`. Because the Smart Cut E2E passed only after the worker1 patches, no worker1 rollback was executed.
