# 0415 Acceptance Report

## Scope
- Version: `0415`
- Slot: `release/0415` test slot on A-machine
- Date: `2026-04-17`

## Deployment Evidence
- A-machine web slot started from uploaded Next standalone runtime:
  - host: `14.103.249.104`
  - process target: `3001`
  - runtime path: `/home/malin/release_0415_slot/web_runtime_af30ae1/.next/standalone`
- A-machine Smart Cut API slot started from `a-scheduler:0415-af30ae1`:
  - host: `14.103.249.104`
  - port: `8001`
  - database: `postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55432/scheduler`
- A-machine scheduler slot started from the same image:
  - container: `release0415_scheduler`
- A-machine worker slot started from `smart-cut-worker-gateway:0.0.3-dev`:
  - container: `release0415_worker`
  - docker stage-runner enabled
  - algorithm image loaded: `website_aicut-smart_cut_worker:latest`

## Domain / Route Evidence
- `https://xiaomajianji.cn/welcome` -> `200 OK`
- `https://xiaomajianji.cn/smart-cut` -> `200 OK`
- `https://xiaomajianji.cn/tasks` -> `200 OK`
- `https://xiaomajianji.cn/tts` -> `200 OK`

These checks were run after the Nginx cutover removed:
- the static `/smart-cut` HTML patch
- the `/welcome` `sub_filter` Smart Cut button injection

## End-to-End Evidence
Validated on business task:
- `0b572a2b-c7cd-45cc-b839-cebb22f0844c`

Observed sequence:
1. `upload-direct` succeeded
2. `analyze` scheduler task executed successfully
3. business task advanced to `waiting_user`
4. `preview` request created edit `83c43bc4-1e4f-450d-868f-e9d6c481d4ae`
5. preview completed and business task advanced back to `waiting_user`
6. `finalize` scheduler task executed successfully
7. business task advanced to `success`
8. task-center user list exposed final download key

Final task detail evidence:
- `status = success`
- `current_stage = complete`
- `audio_b_url = smart-cut/0b572a2b-c7cd-45cc-b839-cebb22f0844c/preview/83c43bc4-1e4f-450d-868f-e9d6c481d4ae/audio_b.mp3`
- `final_video_url = smart-cut/0b572a2b-c7cd-45cc-b839-cebb22f0844c/finalize/final_video.mp4`

Task-center user evidence:
- task appears as `finished`
- `progress = 100`
- `download_url` points to `smart-cut/0b572a2b-c7cd-45cc-b839-cebb22f0844c/finalize/final_video.mp4`

## Fixes Proven During Server Acceptance
- Added `python-multipart` to API dependencies so `upload-direct` can register and run.
- Fixed `TaskDetailResponse` builder to stop reading non-existent `SmartCutEdit.error_message`.
- Fixed worker POST heartbeat handling so scheduler can advance and release workers correctly.
- Mounted docker CLI and stage-runner source into the worker slot.
- Enabled docker stage-runner mode for the worker slot.

## Residual Risks
- Browser-level login flow was not fully automated with Playwright against the live auth service; route availability and API-backed task flow were verified instead.
- The acceptance flow used the staged algorithm-container path (`run_stage_from_manifest.py`) rather than a full real-algorithm media pipeline.
- Legacy failed tasks from earlier test iterations remain in the shared PostgreSQL and appear in task-center history.

## Verdict
- `F10` deployment target is live and reachable.
- `F11` end-to-end acceptance is satisfied for the 0415 Smart Cut -> Task Center core flow.
- `F12` temporary Smart Cut Nginx/static patch cleanup is complete.
