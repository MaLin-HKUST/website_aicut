# 0415 Acceptance Real Data Flow

## Dataset Used
- Video: `/Volumes/XIAOMA-A-1T/wei_videodb/C2384_reencoded.mp4`
- Reference text: `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`
- Edited script source: `tests/test_cujiian/manual_case_config.json`

说明：
- 记录中的原始大文件 `C2384.MP4` 仍然可读
- 本轮部署侧 acceptance 采用同一内容族的 `C2384_reencoded.mp4` 作为可操作的真实样本

## Deployment Target
- A-machine `14.103.249.104`
- API: `http://127.0.0.1:8001`
- Scheduler: `release0415_scheduler`
- Worker: `release0415_worker`

## Result
- Real-data analyze: PASS
- Real-data preview: PASS
- Real-data finalize: PASS

## Evidence Task
- Task ID: `72c84d7c-f9d1-4ea0-b80e-e0a16046b122`

## Final Evidence
- `status = success`
- `current_stage = complete`
- `audio_b_url` exists
- `final_video_url = smart-cut/72c84d7c-f9d1-4ea0-b80e-e0a16046b122/finalize/final_video.mp4`
- `groundtruth_saved = true`

## Notes
- The first finalize attempt happened too early and returned `Pause cuts not available for the selected edit`.
- After preview result persistence settled, rerunning finalize succeeded.
