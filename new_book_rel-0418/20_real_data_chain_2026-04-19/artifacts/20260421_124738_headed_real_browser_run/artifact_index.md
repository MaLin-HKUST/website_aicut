# Artifact Index

## 任务真相

- business task: `542a7196-dbee-4e8f-acb4-7f134f2ba438`
- analyze scheduler task: `14c45353-5cd9-4276-a38f-2eac9694519f`
- preview scheduler task: `8cbeabaa-0544-44b8-b8c4-3a47c93b244d`
- finalize scheduler task: `30be1c22-8694-4940-b9b1-c94a45041bc3`
- active edit: `6a7ed486-fcd8-4bb3-8f28-af2a30430ebb`
- final video key: `smart-cut/542a7196-dbee-4e8f-acb4-7f134f2ba438/finalize/final_video.mp4`

## 优先阅读

1. `summary.md`
2. `sanitized_summary.md`
3. `browser_run_summary.md`
4. `task_detail_final.json`
5. `task_center_final.json`
6. `final_video_head.txt`
7. `db_task_final_snapshot.txt`
8. `scheduler_tasks_final_snapshot.txt`
9. `worker_logs_task_542_excerpt.txt`
10. `playwright_real_task_ui_check.txt`

## 这轮最重要的新信息

- 旧 `upload-direct` 在真实视频上先返回 `413`，但实际浏览器链路已经改为 `upload-prepare -> 浏览器直传 TOS -> upload-complete` 并成功跑通。
- 最新 live chain 证据已经从“手工 finalize 收口”升级为“Worker 自动上传最终视频并自动回写数据库”。
- 当前线上链路虽然闭环成功，但 live PostgreSQL schema 仍没对齐工作台重构要求的 `visible_in_task_center / task_title` 字段。

## 敏感或临时文件

以下文件只保留现场，不应直接带入公共文档或外发：

- `login_cookies.txt`
- `login_headers.txt`
- `login_body.txt`
- 所有含预签名 URL 的 json/txt
- 所有原始 network trace / console trace

详细分类见 `artifact_manifest.json`。
