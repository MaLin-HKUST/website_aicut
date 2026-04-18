# 阶段 7：主链路闭环验收

时间：2026-04-19

## 结论

阶段 7 已完成。

候选中心侧和 Worker 侧已经在真实 TOS 上跑通以下闭环：

1. 创建任务
2. 直接上传输入到真实 TOS
3. analyze
4. preview
5. finalize
6. 最终结果回写业务任务

## 使用的验收任务

业务任务：

- `8dd1797a-7999-48ab-a0c7-76c1b523bd2c`

对应调度任务：

- analyze：`4f92151c-e6e4-4d20-a3b2-9852afa61b65`
- preview：`7143f582-4835-4572-a044-1ff1b8a26eff`
- finalize：`f485b696-8f75-494f-9e6e-bbfcd4f244ba`

对应 preview edit：

- `c1f5751a-3b1d-4448-8384-cdf3a43fc09b`

## 阶段 7 验证结果

### 1. analyze 成功

任务详情已推进到：

- `status = waiting_user`
- `current_stage = user_select`

同时具备真实 TOS 产物：

- `smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/analyze/asr.json`
- `smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/analyze/script.json`
- `smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/analyze/delay_cuts.json`
- `smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/analyze/audio_a.mp3`

### 2. preview 成功

preview 成功后，任务再次回到：

- `status = waiting_user`
- `current_stage = user_select`

并生成了 preview 产物：

- `audio_b_url = smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/preview/c1f5751a-3b1d-4448-8384-cdf3a43fc09b/audio_b.mp3`

Worker 日志也已证明：

- preview 输入下载成功
- preview 输出上传成功
- Edit 状态与 `active_edit_id` 更新成功

### 3. finalize 成功

finalize 之后，业务任务最终推进到：

- `status = success`
- `current_stage = complete`

最终视频 TOS key：

- `smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/finalize/final_video.mp4`

业务任务详情也已返回：

- `final_video_url = smart-cut/8dd1797a-7999-48ab-a0c7-76c1b523bd2c/finalize/final_video.mp4`

## Worker 侧日志摘要

Worker `worker1-phase6-gateway` 已依次记录：

- `Task completed successfully: 4f92151c-e6e4-4d20-a3b2-9852afa61b65`
- `Task completed successfully: 7143f582-4835-4572-a044-1ff1b8a26eff`
- `Task completed successfully: f485b696-8f75-494f-9e6e-bbfcd4f244ba`

这说明 analyze / preview / finalize 三段都在 Worker 机器上完成。

## 正式域名切流

在阶段 7 中，正式域名 `xiaomajianji.cn` 已从旧 `3001` 切到 candidate `3301`。

当前 nginx 统一代理到：

- `127.0.0.1:3301`

切流后验证过的正式域名页面标记：

- `/login` 命中：`小马AI剪辑`、`营销视频剪辑智能体`、`登录`
- `/welcome` 命中：`小马 AI 剪辑`、`小马AI准备就绪`、`请点击左侧`
- `/tts` 命中：`把文案直接转成音频`、`当前音色`

## 风险说明

- 当前公网入口已经切到 candidate 新链路，但 candidate API 和 candidate web 仍包含热补文件，不是完整重建镜像。
- 主链路闭环验证是通过 API 和 Worker 真链路完成的，用户态浏览器页面尚未额外做一整套 Playwright 真实线上闭环。
- `ffprobe` 在 Worker finalize 阶段缺失，因此 finalize 走了保底码率路径，但最终视频仍成功生成。

## 对下一步的直接指令

阶段 7 已完成，可以进入阶段 8 的回滚与恢复演练。
