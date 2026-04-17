# 0415 Acceptance Task Center And Queue

## Scope
- Validate task-center status and download evidence
- Validate queue visibility with more than one task

## Status / Download Evidence
- Finished task used: `72c84d7c-f9d1-4ea0-b80e-e0a16046b122`
- Expected task-center state: `finished`
- Expected download field: `download_url`

## Queue Scenario
- Queue scenario user id: `rel0415-queue-user`
- Scenario creates 3 tasks close together and triggers analyze on all of them
- Expected observation:
  - one task running
  - at least one task queued
  - queued tasks expose `queue_position`

## Result
- Real-data user task-center evidence: PASS
- Admin task-center richer-field evidence: PASS
- Queueing visibility evidence: PASS

## Observed User / Admin Task-Center Evidence
- User query: `GET /api/task-center/tasks?user_id=rel0415-real-user`
- Returned task `72c84d7c-f9d1-4ea0-b80e-e0a16046b122` as:
  - `status = finished`
  - `progress = 100`
  - `download_url = smart-cut/72c84d7c-f9d1-4ea0-b80e-e0a16046b122/finalize/final_video.mp4`
- Admin query: `GET /api/admin/task-center/tasks`
- Returned richer fields for the same task:
  - `user_id = rel0415-real-user`
  - `scheduler_task_id = 61d9d765-24df-4496-86ef-ae1dd7c1c872`
  - `scheduler_status = success`
  - `worker_id = release0415-worker`

## Queueing Observation
- The latest queue scenario snapshot (`queue_acceptance_v5/task_center_user_early.json`) shows:
  - one running task:
    - `b3ec4942-bf4b-42b6-89aa-ea6ab742b67b`
  - two queued tasks with explicit positions:
    - `ef0dfaa8-05f8-4f3e-80ff-0e64dab484a0` -> `queue_position = 2`
    - `6a9c0353-61c5-4d07-a375-d52910030fde` -> `queue_position = 3`

## Verdict For A08
- The current task-center API now exposes explicit queued tasks and queue positions.
- Queueing is no longer an acceptance blocker.
