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
- Queueing visibility evidence: FAIL

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
- Two queue scenarios were executed:
  - normal rapid creation
  - worker-forced-offline rapid creation
- The acceptance goal was to observe explicit `queued` tasks and `queue_position`.
- The current task-center snapshots instead showed new analyze tasks as `running` without queue positions.

## Verdict For A08
- Current 0415 code does not yet provide strong queue-position evidence in Task Center.
- This remains an acceptance blocker if queue visibility is part of the release requirement.
