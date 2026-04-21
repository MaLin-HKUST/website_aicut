# R03 Task Center Visibility Checks

## Query Rule

- `GET /api/task-center/tasks`
- `GET /api/admin/task-center/tasks`

Both queries now apply:

- `smart_cut_tasks.visible_in_task_center = true`

This hides draft-phase tasks from task center even if they still exist in history.

## Hidden Statuses

Legacy or draft tasks are backfilled to hidden when their business status is one of:

- `waiting_upload`
- `ready_analyze`
- `analyzing`
- `waiting_user`
- `previewing`
- `preview_failed`
- `analyze_failed`
- `abandoned`

## Visible Statuses

Formal task-center entries remain visible when status is one of:

- `finalizing`
- `finalize_failed`
- `success`

## Historical Data Handling

- Added script: `scripts/rel0415/backfill_smart_cut_task_center_visibility.py`
- The script adds missing legacy columns when needed:
  - `task_title`
  - `visible_in_task_center`
  - `session_scope_id`
- The script then recomputes `visible_in_task_center` from task status and updates legacy rows in place.
- History is hidden, not deleted.

## Validation Run

- `pytest tests/test_rel0415_api.py -q`
  - Result: `5 passed`
- `python3 -m py_compile apps/api/routes/task_center.py scripts/rel0415/backfill_smart_cut_task_center_visibility.py tests/test_rel0415_api.py`
  - Result: success

## Evidence Covered By Tests

- Hidden `waiting_user` draft is excluded from task-center list.
- Visible `success` task remains in task-center list.
- Finalize still promotes a hidden draft into task center by setting:
  - `visible_in_task_center = true`
  - `task_title = 智能剪气口-YYYYMMDD-HHMMSS`
