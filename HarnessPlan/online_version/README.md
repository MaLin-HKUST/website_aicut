# 智能剪口播 - 在线版模块

这是 aicut2602 算法库之上的在线封装层，用于支持 website_aicut 的三阶段任务流（analyze -> preview -> finalize）。

## 架构

```
online_version/
├── src/
│   ├── __init__.py              # 模块导出
│   ├── paths.py                 # 路径配置
│   ├── models.py                # 数据模型
│   ├── script_formatter.py      # 脚本格式转换（已有）
│   ├── generate_audio_b.py      # 音频 B 生成（已有）
│   ├── pause_mapping.py         # 暂停映射（F08）
│   ├── final_video_cutter.py    # 最终视频切割（F09）
│   ├── analyze_processor.py     # Analyze 处理器（F05）
│   ├── preview_processor.py     # Preview 处理器（F06/F07）
│   ├── finalize_processor.py    # Finalize 处理器（F10）
│   └── groundtruth_recorder.py  # GroundTruth 记录（F11）
└── tests/
    ├── test_script_formatter.py # 脚本格式转换测试（已有）
    ├── test_generate_audio_b.py # 音频 B 生成测试
    ├── test_pause_mapping.py    # 暂停映射测试
    └── test_final_video_cutter.py # 视频切割测试
```

## 三阶段任务流

### 1. Analyze 阶段

- 从 TOS 下载原视频和标准文案
- 执行 `run_raw_cut.py --flow-a`
- 产出：script、ASR、DelayCuts、audio_a

```python
from src.analyze_processor import process_analyze

result = process_analyze(
    task_id="task-123",
    original_video_path="/data/smart-cut/task-123/input/source_video.mp4",
    reference_text_path="/data/smart-cut/task-123/input/reference.txt",
)
```

### 2. Preview 阶段

- 用用户修订后的脚本重新生成 edited_delay_cuts
- 基于 edited_delay_cuts 重新生成 edited_audio_a
- 用 `detect_pauses_on_audio_a()` 生成 pause_cuts_on_audio_a
- 生成 audio_b
- 把 pause_cuts_on_audio_a 映射回原视频时间轴
- 保存 DirectCutter 兼容的 pause_cuts_on_original.json

```python
from src.preview_processor import process_preview

result = process_preview(
    task_id="task-123",
    edited_script="这是{要删除的}内容",
    original_script="这是{要删除的}内容",
    asr_result_path="/data/smart-cut/task-123/analyze/asr.json",
    original_video_path="/data/smart-cut/task-123/input/source_video.mp4",
)
```

### 3. Finalize 阶段

- 基于最后一次成功 preview 的产物生成最终视频
- 支持两种输出模式：original / vertical_1080p
- vertical_1080p 模式需要先调用 normalize_input_video
- 输出码率遵循 `min(input_bitrate, 12Mbps)`

```python
from src.finalize_processor import process_finalize, OutputMode

result = process_finalize(
    task_id="task-123",
    original_video_path="/data/smart-cut/task-123/input/source_video.mp4",
    edited_delay_cuts_path="/data/smart-cut/task-123/preview/edited_delay_cuts.json",
    pause_cuts_on_original_path="/data/smart-cut/task-123/preview/pause_cuts_on_original.json",
    output_mode=OutputMode.VERTICAL_1080P,
)
```

## 核心功能

### 脚本格式转换

```python
from src.script_formatter import (
    script_to_html,      # 大括号 -> HTML <del>
    html_to_script,      # HTML <del> -> 大括号
    script_to_delete_ranges,  # 提取删除范围
    validate_script_format,   # 验证格式
)
```

### 音频 B 生成

```python
from src.generate_audio_b import generate_audio_b

audio_b_path = generate_audio_b(
    audio_a_path="audio_a.mp3",
    delay_cuts=[{"start_time": 10.0, "end_time": 20.0}],
    output_path="audio_b.mp3",
)
```

### 暂停映射

```python
from src.pause_mapping import (
    map_pauses_to_original_seconds,
    dump_pause_cuts_for_direct_cutter,
)

mapped = map_pauses_to_original_seconds(
    pause_cuts_on_audio_a=[{"start_time": 5.0, "end_time": 6.0}],
    delay_cuts=[{"start_time": 2.0, "end_time": 4.0}],
)

dump_pause_cuts_for_direct_cutter(mapped, "pause_cuts_on_original.json")
```

### 最终视频切割

```python
from src.final_video_cutter import OnlineFinalVideoCutter, calculate_output_bitrate

cutter = OnlineFinalVideoCutter("input.mp4")
cutter.load_delay_cuts("delay_cuts.json")
cutter.load_pause_cuts("pause_cuts.json")
cutter.calculate_keep_segments()
cutter.cut(
    "output.mp4",
    video_bitrate=calculate_output_bitrate(8_000_000),
)
```

### GroundTruth 记录

```python
from src.groundtruth_recorder import record_groundtruth, upload_groundtruth

record_result = record_groundtruth(
    task_id="task-123",
    company="company_a",
    reference_text="标准文案",
    original_video_url="...",
    original_video_tos_key="...",
    asr_result={},
    analyze_script="这是{删除}内容",
    edited_script="这是{删除}修改",
    output_dir="/data/smart-cut/task-123/groundtruth",
)

upload_result = upload_groundtruth(
    local_dir="/data/smart-cut/task-123/groundtruth",
    tos_prefix="cujian_input_data/company_a/2024-04/cujian_userdata_20240401_120000",
    upload_fn=upload_fn,
)
```

## 数据模型

### SmartCutTask

```python
from src.models import SmartCutTaskMixin, TaskStatus, OutputMode

class SmartCutTask(Base, SmartCutTaskMixin):
    __tablename__ = "smart_cut_tasks"
```

### SmartCutEdit

```python
from src.models import SmartCutEditMixin

class SmartCutEdit(Base, SmartCutEditMixin):
    __tablename__ = "smart_cut_edits"
```

## 测试

```bash
cd /Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/online_version

# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_script_formatter.py -v
pytest tests/test_generate_audio_b.py -v
pytest tests/test_pause_mapping.py -v
pytest tests/test_final_video_cutter.py -v
```

## 依赖

- Python 3.10+
- FFmpeg（用于音视频处理）
- SQLAlchemy（用于数据模型）
- aicut2602（算法库）

## 路径配置

```python
from src.paths import (
    AI_CUT_ROOT,           # /app/aicut2602
    WEBSITE_ROOT,          # /app/website_aicut
    WORK_BASE_DIR,         # /data/smart-cut
    ensure_task_dirs,      # 确保任务目录存在
)
```

## 规格来源

- 产品规格：`/Users/malin13/Documents/trae_projects/website_aicut/doc/cujian_plan_cx2.md`
- 需求描述：`/Users/malin13/Documents/trae_projects/website_aicut/doc/cujian_prd.md`
