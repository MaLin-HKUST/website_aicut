# F3 Smart Cut Created Order And Worker Artifact Report

## Decision

PASS_WITH_CONDITIONS

## Scope

- Production A Smart Cut API/task center ordering.
- Worker1 Smart Cut runtime patch reconciliation into a reusable runtime artifact.
- aicut2602 video quality probe guard source reconciliation.

Out of scope:

- Marketing Video/B API.
- KDT/RBZJ.
- Cleaning old validation tasks.

## What Changed Online

Production A API source was patched in:

- `/home/malin/release_0425/current_website_aicut/apps/api/routes/task_center.py`
- `/home/malin/release_0425/current_website_aicut/apps/api/routes/tasks.py`

Both user task-center listing and Smart Cut task list now order by:

```text
SmartCutTask.created_at DESC
```

instead of:

```text
SmartCutTask.updated_at DESC
```

The API process was restarted by killing the old user-owned uvicorn process and allowing `smart-cut-api.service` to restart it. `systemctl restart` was unavailable without interactive authentication.

## Online Validation

- `smart-cut-api.service`: active
- API health: `200`
- `/tasks`: `200`
- `/marketing-video`: `200`
- Task-center created-time order proof:
  - old validation task `b5f10a75-25e4-4278-881a-e0d2efae2838` was renamed after newer tasks.
  - its `updated_at` became `2026-05-14T17:48:21.641380`.
  - it remained below newer-created tasks at list index `4`, proving visible list order no longer follows rename/update time.

## Worker1 Runtime Artifact

The previously emergency-hotfixed worker1 runtime has been captured as a reusable artifact:

```text
/data/worker_artifacts/F3-smartcut-worker1-runtime-artifact-20260515-0150.tgz
```

Archive sha256:

```text
103604c749e8fee9b87723b4e05eb362c8dcc707c0f9a86f191faeb195cd94b1
```

Included payload hashes:

```text
bd2bf6f7801c2e4a6bcba353c245a8fbd7cd1a214b5e960a0e9809dc35e9e3eb  finalize_processor.py
6404a50fb3bfe850f3a024851dff02dc841a1f2217301209a0b44e1e2f129ab3  worker/services/pause_cuts.py
3c4823c6607eaf2c1192091aee1c705c635783738759d8355739d95f066c7c34  aicut2602/modules/task_system/video_quality_control.py
8b3ff6287b66be98ed9a649abff640642c2d5649bd9af9fa49c0a5bc0ecd0186  run_worker_0425.sh
```

This artifact is a runtime capture, not a full Docker image. It closes the immediate "only hand-patched files exist" risk, but a later S-line hardening task should still move worker1 into a normal image/build release lane.

## Local Source Reconciliation

This branch records the Smart Cut API ordering fix and the worker-side files proven on worker1:

- `apps/api/routes/task_center.py`
- `apps/api/routes/tasks.py`
- `apps/services/smart_cut_contract.py`
- `worker/processors/finalize_processor.py`
- `worker/services/pause_cuts.py`
- `tests/test_rel0415_api.py`

The aicut2602 source guard is recorded separately in:

```text
hotfix/F3-smartcut-video-quality-probe-guard
```

## Verification

website_aicut:

```text
python3 -m pytest -q tests/test_rel0415_api.py
9 passed

python3 -m py_compile apps/api/routes/task_center.py apps/api/routes/tasks.py apps/services/smart_cut_contract.py worker/processors/finalize_processor.py worker/services/pause_cuts.py
pass

git diff --check
pass
```

aicut2602:

```text
python3 -m pytest -q tests/unit/test_video_quality_control.py
7 passed

python3 -m py_compile modules/task_system/video_quality_control.py tests/unit/test_video_quality_control.py
pass

git diff --check
pass
```

Known local test limitation:

- `tests/test_task_truth_reconcile.py` was not used as a gate for this worktree because the clean source branch does not contain the full live A schema/runtime baseline. It fails on pre-existing schema drift such as `SmartCutTask.status_detail` and `SmartCutDevice.company_id`, not on the created-time ordering patch.

## Rollback

API source backups on A:

```text
/home/malin/website_aicut_prod/backups/f3_created_order_<timestamp>/
```

Worker1 previous emergency backups remain under:

```text
/data/worker_backups/
```

Worker1 was not restarted during F3 because the runtime already matched the captured artifact.

## Remaining Risks

- A release source remains dirty and should not be treated as source of truth.
- Worker1 is still runtime-file based, not Docker/image based.
- Old validation tasks remain in the production task list/history.
