# 智能剪口播气口 - 第一层联调测试

这套脚本用于排除 UI 干扰，直接验证后端三阶段处理链路是否正确：

1. `analyze`：上传视频和文案后，确认能产出 script / ASR / delay_cuts / audio_a
2. `preview`：基于你手动填写的 `edited_script`，确认能产出 audio_b 和 pause 映射
3. `finalize_original`：生成原始尺寸最终视频
4. `finalize_vertical`：生成 1080P 竖屏最终视频
5. `groundtruth`：验证 GroundTruth 目录归档逻辑

## 你需要先填写的内容

先复制一份配置模板：

```bash
cp tests/test_cujiian/manual_case_config.example.json tests/test_cujiian/manual_case_config.json
```

然后编辑：

- `original_video_path`
- `reference_text_path`
- `edited_script`
- `company`

其中：

- `original_video_path`：真实测试视频的绝对路径
- `reference_text_path`：标准文案文件的绝对路径
- `edited_script`：你做完“删除线/反删除线”后的大括号格式脚本

## 脚本执行顺序

```bash
python3 tests/test_cujiian/step01_analyze.py --config tests/test_cujiian/manual_case_config.json
python3 tests/test_cujiian/step02_preview.py --config tests/test_cujiian/manual_case_config.json
python3 tests/test_cujiian/step03_finalize_original.py --config tests/test_cujiian/manual_case_config.json
python3 tests/test_cujiian/step04_finalize_vertical.py --config tests/test_cujiian/manual_case_config.json
python3 tests/test_cujiian/step05_groundtruth.py --config tests/test_cujiian/manual_case_config.json
```

## 输出位置

测试输出统一保存在：

```text
tests/test_cujiian/output/{task_id}/
```

会包含：

- `analyze_result.json`
- `preview_result.json`
- `finalize_original_result.json`
- `finalize_vertical_result.json`
- `groundtruth_result.json`

本地模拟对象存储输出保存在：

```text
tests/test_cujiian/fake_tos/
```

## 人工验收重点

跑完后你重点检查：

1. `analyze_result.json` 里的 `script` 是否合理
2. `preview_result.json` 的 `audio_b_path` 是否可播放
3. `finalize_*_result.json` 里的视频是否真的生成
4. `vertical_1080p` 模式是否生成 `normalized_input.process.json`
5. `groundtruth_result.json` 的 `groundtruth_tos_key` 是否是目录前缀，而不是单个文件

## 环境说明

这些脚本依赖：

- `aicut2602/libs/cut_breakpoints/online_version/src`
- `aicut2602`
- `ffmpeg`
- `ffprobe`

如果本机 Python 环境和在线模块要求不一致，建议在与你实现代码一致的 Python 版本下运行。
