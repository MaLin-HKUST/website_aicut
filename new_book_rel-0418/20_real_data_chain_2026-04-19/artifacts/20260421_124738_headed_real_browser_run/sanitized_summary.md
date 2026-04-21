# Sanitized Summary

这批 artifacts 对应 2026-04-21 正式站 headed 浏览器真实样本回归。

## 结论

- 真实样本任务 `542a7196-dbee-4e8f-acb4-7f134f2ba438` 已闭环成功。
- analyze / preview / finalize 三段调度任务都在 live chain 上执行成功。
- 最终视频对象已存在于 TOS：
  - `smart-cut/542a7196-dbee-4e8f-acb4-7f134f2ba438/finalize/final_video.mp4`
- Worker 日志已证明 finalize 自动上传并自动回写数据库，不再是 2026-04-20 那种手工收口。

## 仍待解决

- 大文件 finalize 上传耗时偏长，用户等待体验仍差。
- live candidate PostgreSQL 仍未显出 `visible_in_task_center / task_title` 这组新工作台契约字段。
- Worker Gateway 仍依赖运行时动态安装 `tos`。

## 推荐证据

- `summary.md`
- `browser_run_summary.md`
- `task_detail_final.json`
- `task_center_final.json`
- `final_video_head.txt`
- `db_task_final_snapshot.txt`
- `scheduler_tasks_final_snapshot.txt`
- `worker_logs_task_542_excerpt.txt`
- `playwright_real_task_ui_check.txt`

## 安全边界

- 本目录仍保留原始现场文件。
- 含 cookie、headers、预签名 URL 的文件不应长期外传。
- 长期引用时优先用本文件、`summary.md` 和 `artifact_index.md`。
