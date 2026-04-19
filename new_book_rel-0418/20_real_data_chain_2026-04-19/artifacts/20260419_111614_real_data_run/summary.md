# 2026-04-20 真实数据联调结果

## 验收任务

- business task: `c10264ad-5f62-4ad9-9731-bffd0e9ce33c`
- analyze scheduler task: `23f074fa-b87c-4d41-9416-8dc928007c04`
- preview scheduler task: `a872b058-cfc7-491c-86be-6b53b3d35844`
- finalize scheduler task: `5dd044b3-f02b-43d4-8026-050ea58c811b`
- active edit: `394bd0e7-c7e5-4626-a7fc-588d0b8bbe82`

## 输入样本

- video: `/Volumes/XIAOMA-A-1T/wei_videodb/C2384_reencoded.mp4`
- reference: `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`

## 通过结论

1. 正式域名链路已使用真实视频和真实参考文案创建任务并上传到真实 TOS。
2. `analyze` 已经不再输出 `mock analyze script`，而是输出真实 Script1 文稿、真实 ASR、真实 DelayCut 与真实 Audio-A。
3. `preview` 已正式成功，`edited_delay_cuts.json`、`pause_cuts_on_original.json`、`audio_b.mp3` 均已落到 TOS。
4. `finalize` 的真实直剪结果已经生成，最终视频对象：
   - `smart-cut/c10264ad-5f62-4ad9-9731-bffd0e9ce33c/finalize/final_video.mp4`
5. 业务任务当前已经是：
   - `status = success`
   - `current_stage = complete`

## 关键证据

- `analyze_real7_complete.json`
- `preview_real7_complete.json`
- `finalize_real7_complete.json`
- `task_detail_final_real7.json`
- `tos_objects_real7.txt`
- `final_video_download_url_real7.json`
- `final_video_range_head_real7.txt`
- `final_video_upload_result_real7.json`

## 本轮手工修复

这次真实链路不是“纯标准发布”跑通的，中间做了这些必要补修：

1. Worker 机器补齐了最小 `aicut2602` 代码包：
   - `libs/asr`
   - `libs/cut_breakpoints`
   - `modules`
2. `worker/stages/run_stage_from_manifest.py` 已从硬编码 mock runner 改成真实执行器：
   - analyze: `run_raw_cut.py --flow-a`
   - preview: `script_to_delay_cuts.py + generate_audio_from_cuts.py`
   - finalize: `run_raw_cut.py --cut-only`
3. `worker/services/algorithm_runner.py` 已补齐 ASR 环境变量透传：
   - `BYTEDANCE_ASR_APPID`
   - `BYTEDANCE_ASR_TOKEN`
4. Worker Gateway 当前启动方式不是纯镜像，而是：
   - 启动时先 `pip install tos`
5. `finalize` 真实直剪虽然成功生成本地 `final_video.mp4`，但 Worker 自动上传和状态回写没有完成。
   - 本轮最终采用“本机复刻 finalize + 本机上传 TOS + 手工修正 PostgreSQL 状态”的方式收口。

## 仍然存在的缺口

1. Worker Gateway 仍依赖启动时动态安装 `tos`，不是纯净镜像。
2. `finalize` 自动回传链路仍有 bug：
   - Worker 本地已生成 `final_video.mp4`
   - 但自动上传到 TOS 和自动回写 `smart_cut_tasks` / `scheduler_tasks` 没有稳定完成
3. `analyze` / `preview` / `finalize` 虽然都已在真实数据上证明可执行，但最后一段收口仍依赖手工状态修正。

## 对下一个 Agent 的直接指令

- 不要再把当前系统描述成“仍然只有 mock 链路”。
- 也不要误判成“已经纯自动化收口完成”。
- 当前最准确的表述是：
  - `真实样本 A/B/C 链路已经跑通`
  - `最终视频已落 TOS`
  - `但 Worker finalize 自动回传与标准发布收口仍需继续修`
