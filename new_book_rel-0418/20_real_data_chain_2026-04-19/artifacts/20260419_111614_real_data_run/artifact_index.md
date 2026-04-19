# Artifact Index

## 任务真相

- business task: `c10264ad-5f62-4ad9-9731-bffd0e9ce33c`
- analyze scheduler task: `23f074fa-b87c-4d41-9416-8dc928007c04`
- preview scheduler task: `a872b058-cfc7-491c-86be-6b53b3d35844`
- finalize scheduler task: `5dd044b3-f02b-43d4-8026-050ea58c811b`
- active edit: `394bd0e7-c7e5-4626-a7fc-588d0b8bbe82`
- final video key: `smart-cut/c10264ad-5f62-4ad9-9731-bffd0e9ce33c/finalize/final_video.mp4`

## 优先阅读

1. `summary.md`
2. `sanitized_summary.md`
3. `analyze_real7_complete.json`
4. `preview_real7_complete.json`
5. `finalize_real7_complete.json`
6. `task_detail_final_real7.json`
7. `tos_objects_real7.txt`
8. `local_multipart_smoke.json`
9. `playwright_real_task_ui_check.txt`

## 敏感或临时文件

以下文件只保留现场，不应进入版本库：

- `session_cookie.txt`
- 所有 `*upload_url*` / `*download_url*` / `*put_url*` 文件
- 所有 `*put_headers*` / `*put_body*` 文件

## 文件分类

- `primary_evidence`: 可直接支撑“真实任务已闭环，但 finalize 自动收口未完成”
- `primary_evidence` 里现在还包含：
  - `local_multipart_smoke.json`：真实 bucket 上的 multipart 上传烟雾
  - `playwright_real_task_ui_check.txt`：正式站真实任务 UI 观测验收输出
- `run_context`: 本轮执行前置和样本信息
- `request_trace`: 请求/轮询/headers/payload 级别痕迹
- `step_output`: 各阶段中间结果
- `debug`: 额外排障材料

详细分类见 `artifact_manifest.json`。
