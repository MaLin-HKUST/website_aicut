# Sanitized Summary

这批 artifacts 对应 2026-04-20 真实样本正式链路验收。

## 结论

- 真实样本任务 `c10264ad-5f62-4ad9-9731-bffd0e9ce33c` 已闭环成功。
- `analyze / preview / finalize` 都在真实数据上跑过。
- 最终视频对象已经存在于 TOS：
  - `smart-cut/c10264ad-5f62-4ad9-9731-bffd0e9ce33c/finalize/final_video.mp4`
- 该轮成功依赖手工收口：本机复刻 finalize、本机上传最终视频、手工修正 PostgreSQL 状态。

## 仍待解决

- Worker finalize 自动上传最终视频到 TOS 仍有缺口。
- `scheduler_tasks / smart_cut_tasks` 的最终成功状态本轮不是纯自动推进。
- Worker Gateway 仍依赖启动时动态安装 `tos`。

## 推荐证据

- `summary.md`
- `analyze_real7_complete.json`
- `preview_real7_complete.json`
- `finalize_real7_complete.json`
- `task_detail_final_real7.json`
- `tos_objects_real7.txt`
- `local_multipart_smoke.json`
- `playwright_real_task_ui_check.txt`

## 安全边界

- 本目录保留了原始现场文件。
- 不要把含 cookie、预签名 URL、上传地址的文件带入版本库。
- 长期引用时优先使用本文件和 `summary.md`，再回看原始 traces。
