# 2026-04-21 Headed 浏览器真实回归结果

## 验收任务

- business task: `542a7196-dbee-4e8f-acb4-7f134f2ba438`
- analyze scheduler task: `14c45353-5cd9-4276-a38f-2eac9694519f`
- preview scheduler task: `8cbeabaa-0544-44b8-b8c4-3a47c93b244d`
- finalize scheduler task: `30be1c22-8694-4940-b9b1-c94a45041bc3`
- active edit: `6a7ed486-fcd8-4bb3-8f28-af2a30430ebb`
- final video key: `smart-cut/542a7196-dbee-4e8f-acb4-7f134f2ba438/finalize/final_video.mp4`

## 输入样本

- video: `/Volumes/XIAOMA-A-1T/wei_videodb/C2384_reencoded.mp4`
- reference: `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`
- account: `rbzj / 123456`
- base url: `https://xiaomajianji.cn`
- artifact dir: `new_book_rel-0418/20_real_data_chain_2026-04-19/artifacts/20260421_124738_headed_real_browser_run`

## 通过结论

1. 正式站 headed 浏览器链路已经完整走通：
   - 登录
   - `/smart-cut`
   - 上传真实视频
   - 上传真实文案
   - analyze
   - 页面内最小合法删除编辑
   - preview
   - finalize
   - `/tasks` 下载入口观测
2. 这轮浏览器回归中，旧 `upload-direct` 主路径先返回了 `413`，但实际浏览器链路已经通过：
   - `upload-prepare`
   - 浏览器直传 TOS
   - `upload-complete`
   成功进入 `ready_analyze`。
3. A 机 PostgreSQL 当前任务行已经是：
   - `status = SUCCESS`
   - `current_stage = COMPLETE`
   - `active_edit_id = 6a7ed486-fcd8-4bb3-8f28-af2a30430ebb`
   - `final_video_url = smart-cut/542a7196-dbee-4e8f-acb4-7f134f2ba438/finalize/final_video.mp4`
4. A 机调度表中已存在并成功完成三条调度任务：
   - `SMART_CUT_ANALYZE`
   - `SMART_CUT_PREVIEW`
   - `SMART_CUT_FINALIZE`
   三条任务都分配给 `worker1-phase6`。
5. Worker `worker1-phase6-gateway` 日志已经证明：
   - analyze 下载了真实输入
   - analyze 上传了 `script.json / asr.json / delay_cuts.json / audio_a.mp3`
   - finalize 最终执行到 `Business task marked as success`
   - finalize 自动上传并回写了 `smart-cut/542a7196-dbee-4e8f-acb4-7f134f2ba438/finalize/final_video.mp4`
6. 最终视频对象可被直接 HEAD 到：
   - `HTTP/1.1 200 OK`
   - `Content-Length: 164697370`
   - `x-tos-mp-parts-count: 32`
7. 当前时点补跑的 headed Playwright 观测也通过：
   - `apps/web/tests/rel0415-smart-cut-real-task.spec.ts`
   - 结果：`1 passed`

## 关键证据

- `browser_run_summary.md`
- `upload_failure_note.txt`
- `upload_prepare_response.json`
- `upload_complete.json`
- `task_detail_after_upload.json`
- `task_detail_final.json`
- `task_center_final.json`
- `final_video_head.txt`
- `db_schema_smart_cut_tasks.txt`
- `db_task_final_snapshot.txt`
- `scheduler_tasks_final_snapshot.txt`
- `worker_logs_task_542_excerpt.txt`
- `playwright_real_task_ui_check.txt`

## 当前风险与未收口项

1. 这轮成功不再依赖“本机复刻 finalize + 手工回写数据库”；最新证据显示 live chain 已自动收口成功。
2. 但最终视频上传耗时仍偏长：
   - `164697370` bytes
   - `32` 个 multipart 分片
   - 用户侧长时间等待仍需专项优化。
3. 当前 live candidate PostgreSQL 里的 `smart_cut_tasks` 仍是旧 schema，只看到：
   - `status`
   - `current_stage`
   - `active_edit_id`
   - `final_video_url`
   等旧字段
   而看不到 repo 中本轮工作台重构约定的：
   - `visible_in_task_center`
   - `task_title`
   这说明“真实链路跑通”不等于“新工作台契约已完整部署到线上”。
4. Worker Gateway 仍依赖运行时 `pip install tos`，不是纯净镜像发布。
5. candidate API / Worker 热补仍未完全回收进标准构建与标准部署流程。
