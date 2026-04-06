# 智能剪口播气口功能开发计划（最终修订版）

## 核心原则

1. **三阶段离散任务**：analyze → preview → finalize，Worker 不阻塞等待用户
2. **normalize 移至 finalize**：用户在最终输出前选择规格，analyze/preview 始终基于原始视频
3. **代码隔离**：所有新代码放在 `aicut2602/libs/cut_breakpoints/online_version/`，不修改原代码
4. **audio_b 仅用于试听**：最终视频由 DirectCutter 基于原视频 + cuts 直接生成

---

## 目录结构

```
aicut2602/libs/cut_breakpoints/online_version/
├── src/
│   ├── __init__.py
│   ├── generate_audio_b.py          # 新增：生成试听 audio_b
│   ├── pause_mapping.py             # 新增：PauseCuts 时间轴映射封装
│   ├── finalize_processor.py        # 新增：finalize 阶段处理器（含 normalize 选择逻辑）
│   ├── analyze_processor.py         # 新增：analyze 阶段封装
│   ├── preview_processor.py         # 新增：preview 阶段封装
│   └── script_formatter.py          # 新增：大括号 ↔ ranges 转换工具
├── workers/
│   ├── __init__.py
│   ├── analyze_worker.py            # Worker: analyze 任务
│   ├── preview_worker.py            # Worker: preview 任务
│   └── finalize_worker.py           # Worker: finalize 任务（含输出规格选择）
└── tests/
    └── test_online_version.py
```

---

## 第一部分：新增模块详细设计

### 1.1 generate_audio_b.py

```python
"""
生成用于试听的 audio_b
基于 audio_a 和 PauseCuts（audio_a 时间轴）生成剪掉停顿的音频
"""
from dataclasses import dataclass
from typing import List, Dict
import subprocess
import tempfile
import os


@dataclass
class AudioBResult:
    success: bool
    output_path: str
    original_duration: float      # audio_a 时长
    keep_duration: float          # audio_b 时长
    cut_duration: float           # 剪掉的总停顿时长


def generate_audio_b(
    audio_a_path: str,
    pause_cuts: List[Dict],       # 格式: [{'start_time': float, 'end_time': float}, ...]
    output_path: str
) -> AudioBResult:
    """
    从 audio_a 中剪掉停顿，生成 audio_b（仅用于试听）
    
    步骤：
    1. 计算保留片段（invert pause_cuts）
    2. FFmpeg 提取并拼接保留片段
    """
    # 获取 audio_a 时长
    duration = _get_audio_duration(audio_a_path)
    
    # 计算保留片段
    keep_segments = _calculate_keep_segments(pause_cuts, duration)
    
    # FFmpeg 拼接
    if len(keep_segments) == 0:
        return AudioBResult(success=False, output_path="", original_duration=duration, keep_duration=0, cut_duration=duration)
    
    if len(keep_segments) == 1:
        # 直接裁剪
        _extract_segment(audio_a_path, keep_segments[0], output_path)
    else:
        # 多段拼接
        _concat_segments(audio_a_path, keep_segments, output_path)
    
    keep_duration = sum(s['end'] - s['start'] for s in keep_segments)
    
    return AudioBResult(
        success=True,
        output_path=output_path,
        original_duration=duration,
        keep_duration=keep_duration,
        cut_duration=duration - keep_duration
    )


def _get_audio_duration(path: str) -> float:
    """使用 ffprobe 获取音频时长"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _calculate_keep_segments(pause_cuts: List[Dict], total_duration: float) -> List[Dict]:
    """根据 pause_cuts 计算需要保留的片段"""
    if not pause_cuts:
        return [{'start': 0.0, 'end': total_duration}]
    
    # 排序
    sorted_cuts = sorted(pause_cuts, key=lambda x: x['start_time'])
    
    keep_segments = []
    current_pos = 0.0
    
    for cut in sorted_cuts:
        if current_pos < cut['start_time']:
            keep_segments.append({
                'start': current_pos,
                'end': cut['start_time']
            })
        current_pos = max(current_pos, cut['end_time'])
    
    if current_pos < total_duration:
        keep_segments.append({
            'start': current_pos,
            'end': total_duration
        })
    
    return keep_segments


def _extract_segment(input_path: str, segment: Dict, output_path: str):
    """提取单一片段"""
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-i', input_path,
        '-ss', str(segment['start']),
        '-to', str(segment['end']),
        '-c', 'copy',
        output_path
    ]
    subprocess.run(cmd, check=True)


def _concat_segments(input_path: str, segments: List[Dict], output_path: str):
    """拼接多段音频"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 提取各段
        segment_files = []
        for i, seg in enumerate(segments):
            seg_path = os.path.join(temp_dir, f'seg_{i:04d}.mp3')
            _extract_segment(input_path, seg, seg_path)
            segment_files.append(seg_path)
        
        # 创建 concat list
        list_path = os.path.join(temp_dir, 'concat_list.txt')
        with open(list_path, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{seg_file}'\n")
        
        # 拼接
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-f', 'concat', '-safe', '0',
            '-i', list_path,
            '-c', 'copy',
            output_path
        ]
        subprocess.run(cmd, check=True)
```

### 1.2 pause_mapping.py

```python
"""
PauseCuts 时间轴映射
将 PauseCuts 从 audio_a 时间轴 (Ta) 映射回原视频时间轴 (T0)

使用 TimelineMapper 实现，封装成独立模块供 preview/finalize 使用
"""
from typing import List, Dict
import sys
from pathlib import Path

# 引入原代码的 TimelineMapper
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from time_mapping import TimelineMapper, TimeSegment


def map_pauses_to_original(
    pause_cuts_on_audio_a: List[Dict],
    delay_cuts: List[Dict],
    original_duration: float
) -> List[Dict]:
    """
    将 PauseCuts 从 audio_a 时间轴映射回原视频时间轴
    
    Args:
        pause_cuts_on_audio_a: 在 audio_a 时间轴上的停顿段
        delay_cuts: A剪辑删除段（原视频时间轴）
        original_duration: 原视频总时长
    
    Returns:
        在原视频时间轴上的停顿段
    """
    # 创建 TimelineMapper
    mapper = TimelineMapper(delay_cuts, original_duration)
    
    # 构建 Index_A
    mapper.build_timeline_a()
    mapper.build_index_a()
    
    # 转换每个 pause_cut
    mapped_pauses = []
    for pause in pause_cuts_on_audio_a:
        # 转换开始和结束时间
        start_t0 = mapper.convert_ta_to_t0(pause['start_time'])
        end_t0 = mapper.convert_ta_to_t0(pause['end_time'])
        
        mapped_pauses.append({
            'start_time': start_t0,
            'end_time': end_t0,
            'duration': end_t0 - start_t0,
            'type': pause.get('type', 'pause')
        })
    
    return mapped_pauses


def build_final_cuts(
    delay_cuts: List[Dict],
    pause_cuts_on_original: List[Dict],
    original_duration: float
) -> List[Dict]:
    """
    构建最终剪辑方案：DelayCuts + PauseCuts（都在原视频时间轴）
    
    使用 TimelineMapper 的 process 方法或手动合并
    """
    # 合并所有 cuts（DelayCuts 和 PauseCuts）
    all_cuts = delay_cuts + pause_cuts_on_original
    
    # 按开始时间排序
    all_cuts.sort(key=lambda x: x['start_time'])
    
    # 合并重叠段
    merged_cuts = []
    for cut in all_cuts:
        if not merged_cuts:
            merged_cuts.append(cut)
        else:
            last = merged_cuts[-1]
            if cut['start_time'] <= last['end_time']:
                # 合并
                last['end_time'] = max(last['end_time'], cut['end_time'])
                last['duration'] = last['end_time'] - last['start_time']
            else:
                merged_cuts.append(cut)
    
    return merged_cuts
```

### 1.3 analyze_processor.py

```python
"""
Analyze 阶段处理器
调用原代码的 run_raw_cut.py 完成 Step A
"""
import subprocess
import json
from pathlib import Path
from typing import Dict


def run_analyze(
    video_path: str,
    reference_path: str,
    output_dir: str,
    task_id: str
) -> Dict:
    """
    运行 analyze 阶段
    
    注意：始终基于原始视频，不做 normalize
    
    Returns:
        {
            'script1_path': str,
            'audio_a_path': str,
            'delay_cuts_path': str,
            'asr_result_path': str,
            'original_text_path': str
        }
    """
    # 调用原代码的 run_raw_cut.py --flow-a
    cmd = [
        'python', 'libs/cut_breakpoints/src/run_raw_cut.py',
        '-i', video_path,
        '-r', reference_path,
        '-o', output_dir,
        '--flow-a'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Analyze failed: {result.stderr}")
    
    # 解析输出路径
    base_name = Path(video_path).stem
    
    return {
        'script1_path': str(Path(output_dir) / f"{base_name}_Script1.txt"),
        'audio_a_path': str(Path(output_dir) / f"{base_name}_audio_a.mp3"),
        'delay_cuts_path': str(Path(output_dir) / f"{base_name}_DelayCutSegments.json"),
        'asr_result_path': str(Path(output_dir) / f"{base_name}_ASR.Result.json"),
        'original_text_path': str(Path(output_dir) / f"{base_name}_原文.TXT")
    }
```

### 1.4 preview_processor.py

```python
"""
Preview 阶段处理器
基于用户编辑的 script 重新生成 audio_a + PauseCut + audio_b
"""
from typing import Dict, List
import sys
from pathlib import Path

# 引入原代码模块
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from script_to_delay_cuts import ScriptToDelayCuts
from pause_detect import PauseDetector, detect_pauses_on_audio_a

# 引入 online_version 新增模块
from .generate_audio_b import generate_audio_b
from .pause_mapping import map_pauses_to_original


def run_preview(
    edited_script_path: str,          # 用户编辑后的 Script1（大括号格式）
    asr_result_path: str,
    original_video_path: str,
    output_dir: str,
    task_id: str
) -> Dict:
    """
    运行 preview 阶段
    
    步骤：
    1. 重新生成 DelayCuts（基于用户编辑的 script）
    2. 重新生成 audio_a
    3. PauseCut 检测（在 audio_a 上）
    4. 生成 audio_b（仅试听）
    5. 将 PauseCuts 映射回原视频时间轴（供 finalize 使用）
    
    Returns:
        {
            'edited_delay_cuts_path': str,
            'edited_audio_a_path': str,
            'pause_cuts_on_audio_a_path': str,
            'pause_cuts_on_original_path': str,  # 映射后的，供 finalize 使用
            'audio_b_path': str
        }
    """
    # 1. 重新生成 DelayCuts
    converter = ScriptToDelayCuts(asr_result_path=asr_result_path)
    delay_cuts_result = converter.convert(
        script1_path=edited_script_path,
        output_path=f"{output_dir}/edited_delay_cuts.json",
        video_path=original_video_path,
        audio_output_path=f"{output_dir}/edited_audio_a.mp3"
    )
    
    edited_delay_cuts = delay_cuts_result['segments']
    edited_audio_a_path = f"{output_dir}/edited_audio_a.mp3"
    
    # 2. PauseCut 检测（在 audio_a 时间轴上）
    pause_cuts_on_audio_a = detect_pauses_on_audio_a(
        asr_path=Path(asr_result_path),
        a_cuts=edited_delay_cuts
    )
    
    # 保存 pause_cuts_on_audio_a
    pause_cuts_audio_a_path = f"{output_dir}/pause_cuts_on_audio_a.json"
    _save_json(pause_cuts_on_audio_a, pause_cuts_audio_a_path)
    
    # 3. 生成 audio_b（仅试听）
    audio_b_path = f"{output_dir}/audio_b.mp3"
    audio_b_result = generate_audio_b(
        audio_a_path=edited_audio_a_path,
        pause_cuts=pause_cuts_on_audio_a,
        output_path=audio_b_path
    )
    
    if not audio_b_result.success:
        raise RuntimeError("Failed to generate audio_b")
    
    # 4. 将 PauseCuts 映射回原视频时间轴
    # 获取原视频时长
    original_duration = _get_video_duration(original_video_path)
    
    pause_cuts_on_original = map_pauses_to_original(
        pause_cuts_on_audio_a=pause_cuts_on_audio_a,
        delay_cuts=edited_delay_cuts,
        original_duration=original_duration
    )
    
    pause_cuts_original_path = f"{output_dir}/pause_cuts_on_original.json"
    _save_json(pause_cuts_on_original, pause_cuts_original_path)
    
    return {
        'edited_delay_cuts_path': f"{output_dir}/edited_delay_cuts.json",
        'edited_audio_a_path': edited_audio_a_path,
        'pause_cuts_on_audio_a_path': pause_cuts_audio_a_path,
        'pause_cuts_on_original_path': pause_cuts_original_path,
        'audio_b_path': audio_b_path
    }


def _save_json(data: List[Dict], path: str):
    """保存 JSON 文件"""
    import json
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_video_duration(path: str) -> float:
    """获取视频时长"""
    import subprocess
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())
```

### 1.5 finalize_processor.py

```python
"""
Finalize 阶段处理器
根据用户选择的输出规格生成最终视频
"""
from typing import Dict, Literal
from pathlib import Path
import subprocess
import json

# 引入原代码模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from direct_cutter import DirectCutter


def run_finalize(
    original_video_path: str,
    delay_cuts_path: str,
    pause_cuts_on_original_path: str,
    output_dir: str,
    task_id: str,
    output_mode: Literal['original', 'vertical_1080p'] = 'original',
    input_bitrate: int = None
) -> Dict:
    """
    运行 finalize 阶段
    
    Args:
        output_mode: 'original' - 原视频规格，'vertical_1080p' - 1080P竖屏
        input_bitrate: 输入视频码率(bps)，用于计算输出码率 min(input_bitrate, 12Mbps)
    
    步骤：
    1. 如果 output_mode='vertical_1080p'，先 normalize 视频
    2. 使用 DirectCutter 剪辑（基于 DelayCuts + PauseCuts）
    3. 记录编码参数
    
    Returns:
        {
            'final_video_path': str,
            'normalized_video_path': str or None,
            'encoding_params': Dict
        }
    """
    # 确定实际要剪辑的视频
    video_to_cut = original_video_path
    normalized_video_path = None
    
    if output_mode == 'vertical_1080p':
        # 先 normalize
        normalized_video_path = f"{output_dir}/normalized_input.mp4"
        _normalize_video(original_video_path, normalized_video_path)
        video_to_cut = normalized_video_path
    
    # 计算输出码率
    output_bitrate = _calculate_output_bitrate(input_bitrate)
    
    # 使用 DirectCutter 剪辑
    final_video_path = f"{output_dir}/final_video.mp4"
    
    cutter = DirectCutter(video_to_cut)
    cutter.load_delay_cuts(delay_cuts_path)
    
    if Path(pause_cuts_on_original_path).exists():
        cutter.load_pause_cuts(pause_cuts_on_original_path)
    
    cutter.calculate_keep_segments()
    
    # 自定义 FFmpeg 参数（码率）
    _cut_with_bitrate(cutter, final_video_path, output_bitrate)
    
    # 记录编码参数
    encoding_params = {
        'output_mode': output_mode,
        'input_bitrate_bps': input_bitrate,
        'output_bitrate_bps': output_bitrate,
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'preset': 'veryfast',
        'crf': 18
    }
    
    # 保存编码参数记录
    params_path = f"{output_dir}/encoding_params.json"
    with open(params_path, 'w') as f:
        json.dump(encoding_params, f, indent=2)
    
    return {
        'final_video_path': final_video_path,
        'normalized_video_path': normalized_video_path,
        'encoding_params': encoding_params
    }


def _normalize_video(input_path: str, output_path: str):
    """归一化视频为 1080P 竖屏"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'incoming_video_process'))
    from libs.incoming_video_process import video_incoming_process
    
    result = video_incoming_process(
        input_path=input_path,
        output_path=output_path,
        preset="1080p",
        landscape_mode="crop",
        speed="production"
    )
    
    if not result.get("ok"):
        raise RuntimeError(f"Normalize failed: {result.get('stderr', '')}")


def _calculate_output_bitrate(input_bitrate: int = None) -> int:
    """
    计算输出码率：min(input_bitrate, 12Mbps)
    """
    MAX_BITRATE = 12_000_000  # 12 Mbps
    
    if input_bitrate is None:
        return MAX_BITRATE
    
    return min(input_bitrate, MAX_BITRATE)


def _cut_with_bitrate(cutter, output_path: str, bitrate: int):
    """使用自定义码率剪辑"""
    # 获取 filter_complex
    filter_complex = cutter.generate_ffmpeg_filter_complex()
    
    cmd = [
        'ffmpeg', '-y',
        '-i', cutter.video_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-b:v', str(bitrate),
        '-maxrate', str(int(bitrate * 1.5)),
        '-bufsize', str(bitrate * 2),
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        output_path
    ]
    
    subprocess.run(cmd, check=True)


def probe_video_bitrate(video_path: str) -> int:
    """探测视频码率(bps)"""
    import subprocess
    import json
    
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=bit_rate',
        '-of', 'json',
        video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    if 'streams' in data and len(data['streams']) > 0:
        bitrate_str = data['streams'][0].get('bit_rate')
        if bitrate_str:
            return int(bitrate_str)
    
    # 如果无法获取，返回 None（将使用默认 12Mbps）
    return None
```

### 1.6 script_formatter.py

```python
"""
Script 格式转换工具
大括号格式 ↔ 结构化 ranges（供前端编辑器使用）
"""
import re
from typing import List, Dict, Tuple


def brackets_to_ranges(text: str) -> Tuple[str, List[Dict]]:
    """
    将大括号格式转换为纯文本 + ranges
    
    Args:
        text: "这是文案{要删除的部分}继续文案"
    
    Returns:
        ("这是文案要删除的部分继续文案", [{"start": 4, "end": 12}])
    """
    ranges = []
    result_chars = []
    current_pos = 0
    i = 0
    
    while i < len(text):
        if text[i] == '{':
            # 找到匹配的 }
            end_brace = text.find('}', i)
            if end_brace == -1:
                # 没有闭合，当作普通字符
                result_chars.append(text[i])
                i += 1
                current_pos += 1
            else:
                # 记录 range
                content_start = current_pos
                content = text[i+1:end_brace]
                result_chars.extend(content)
                content_end = current_pos + len(content)
                ranges.append({'start': content_start, 'end': content_end})
                current_pos = content_end
                i = end_brace + 1
        elif text[i] == '}':
            # 多余的 }，跳过
            i += 1
        else:
            result_chars.append(text[i])
            current_pos += 1
            i += 1
    
    return ''.join(result_chars), ranges


def ranges_to_brackets(text: str, ranges: List[Dict]) -> str:
    """
    将纯文本 + ranges 转换为大括号格式
    
    Args:
        text: "这是文案要删除的部分继续文案"
        ranges: [{"start": 4, "end": 12}]
    
    Returns:
        "这是文案{要删除的部分}继续文案"
    """
    # 从后往前插入大括号，避免索引偏移
    chars = list(text)
    sorted_ranges = sorted(ranges, key=lambda x: x['start'], reverse=True)
    
    for r in sorted_ranges:
        start = r['start']
        end = r['end']
        if start < 0 or end > len(text) or start >= end:
            continue
        chars.insert(end, '}')
        chars.insert(start, '{')
    
    return ''.join(chars)


def validate_bracket_balance(text: str) -> bool:
    """验证大括号是否匹配"""
    count = 0
    for char in text:
        if char == '{':
            count += 1
        elif char == '}':
            count -= 1
            if count < 0:
                return False
    return count == 0


def extract_deleted_text(text: str) -> List[str]:
    """提取所有被大括号标记的文本"""
    pattern = r'\{([^}]*)\}'
    return re.findall(pattern, text)
```

---

## 第二部分：数据库模型（修订版）

```sql
-- 任务主表
CREATE TABLE smart_cut_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- 状态：created, analyzing, analyzed, previewing, preview_ready, finalizing, success, failed
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    
    -- === 输入文件 ===
    original_video_url TEXT NOT NULL,
    reference_text_url TEXT NOT NULL,
    
    -- 输入视频元数据（用于 finalize 码率计算）
    input_video_width INTEGER,
    input_video_height INTEGER,
    input_video_duration FLOAT,
    input_video_bitrate INTEGER,           -- bps
    
    -- === Stage 1: analyze 产物 ===
    asr_result_url TEXT,
    script1_url TEXT,                      -- AI 生成的 script（大括号格式）
    delay_cuts_url TEXT,                   -- 基于 AI script 的 delay_cuts
    audio_a_url TEXT,                      -- 基于 AI script 的 audio_a
    original_text_url TEXT,                -- ASR 原文
    
    analyze_completed_at TIMESTAMP,
    
    -- === Stage 2: preview 产物 ===
    user_edited_script TEXT,               -- 用户编辑后的 script（大括号格式）
    edited_delay_cuts_url TEXT,            -- 基于用户编辑的 delay_cuts
    edited_audio_a_url TEXT,               -- 基于用户编辑的 audio_a
    
    pause_cuts_on_audio_a_url TEXT,        -- 在 audio_a 时间轴上的 pause_cuts
    pause_cuts_on_original_url TEXT,       -- 映射到原视频时间轴的 pause_cuts（供 finalize 使用）
    
    audio_b_url TEXT,                      -- 仅用于试听的 audio_b
    
    preview_completed_at TIMESTAMP,
    
    -- === Stage 3: finalize 产物 ===
    -- 用户选择的输出规格
    output_mode VARCHAR(20),               -- 'original' | 'vertical_1080p'
    
    -- normalize 产物（如选择了 vertical_1080p）
    normalized_video_url TEXT,
    normalized_process_url TEXT,           -- normalize 处理记录
    
    -- 最终产物
    final_video_url TEXT,
    
    -- 最终编码参数记录
    final_encoding_params JSONB,           -- {bitrate, codec, preset, crf, ...}
    
    finalize_completed_at TIMESTAMP,
    
    -- === 工作目录记录（用于问题排查）===
    work_dir TEXT,
    
    -- === 错误信息 ===
    error_message TEXT,
    error_stage VARCHAR(20),               -- analyze | preview | finalize
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 编辑历史（支持多次 preview）
CREATE TABLE smart_cut_previews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES smart_cut_tasks(id),
    
    user_edited_script TEXT NOT NULL,
    edited_delay_cuts_url TEXT,
    edited_audio_a_url TEXT,
    pause_cuts_on_audio_a_url TEXT,
    pause_cuts_on_original_url TEXT,
    audio_b_url TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 第三部分：API 设计（修订版）

### 3.1 创建任务

```http
POST /api/smart-cut/tasks
Content-Type: multipart/form-data

video: <文件>
reference: <文件>

Response:
{
  "task_id": "uuid",
  "status": "created"
}
```

### 3.2 开始 analyze

```http
POST /api/smart-cut/tasks/{id}/analyze

Response:
{
  "task_id": "uuid",
  "status": "analyzing"
}
```

### 3.3 获取 analyze 结果

```http
GET /api/smart-cut/tasks/{id}

Response:
{
  "task_id": "uuid",
  "status": "analyzed",
  
  -- script: 纯文本大括号格式
  "script": "这是文案{要删除的部分}继续文案",
  
  -- 前端用 ranges 渲染删除线
  "delete_ranges": [{"start": 4, "end": 12}],
  
  "audio_a_url": "https://...",
  "duration": 125.5
}
```

### 3.4 提交 preview

```http
POST /api/smart-cut/tasks/{id}/preview
Content-Type: application/json

{
  -- 纯文本大括号格式
  "edited_script": "这是文案{要删除的部分}继续文案"
}

Response:
{
  "task_id": "uuid",
  "status": "previewing"
}
```

### 3.5 获取 preview 结果

```http
GET /api/smart-cut/tasks/{id}

Response:
{
  "task_id": "uuid",
  "status": "preview_ready",
  
  "script": "这是文案{要删除的部分}继续文案",
  "delete_ranges": [{"start": 4, "end": 12}],
  
  "audio_a_url": "https://...",      -- 基于用户编辑的 audio_a
  "audio_b_url": "https://...",      -- 剪掉停顿后的 audio_b（试听用）
  "audio_b_duration": 118.3
}
```

### 3.6 提交 finalize

```http
POST /api/smart-cut/tasks/{id}/finalize
Content-Type: application/json

{
  -- 用户选择输出规格
  "output_mode": "original" | "vertical_1080p"
}

Response:
{
  "task_id": "uuid",
  "status": "finalizing"
}
```

### 3.7 获取 finalize 结果

```http
GET /api/smart-cut/tasks/{id}

Response:
{
  "task_id": "uuid",
  "status": "success",
  
  "final_video_url": "https://...",
  "output_mode": "vertical_1080p",
  
  "encoding_params": {
    "output_mode": "vertical_1080p",
    "input_bitrate_bps": 8000000,
    "output_bitrate_bps": 8000000,
    "video_codec": "libx264",
    "preset": "veryfast"
  },
  
  -- 如使用了 normalize
  "normalized_video_url": "https://..."
}
```

---

## 第四部分：Worker 设计

### 4.1 analyze_worker.py

```python
"""Worker: analyze 任务"""

def process_analyze_task(task_id: str, work_dir: str):
    """
    1. 下载原始视频和文案到 work_dir/input/
    2. 调用 analyze_processor.run_analyze()
    3. 上传产物到 TOS
    4. 更新任务状态为 analyzed
    5. 记录输入视频元数据（码率等）
    """
```

### 4.2 preview_worker.py

```python
"""Worker: preview 任务"""

def process_preview_task(task_id: str, work_dir: str):
    """
    1. 下载必要产物（原视频、ASR、用户编辑的 script）
    2. 调用 preview_processor.run_preview()
    3. 上传产物到 TOS
    4. 更新任务状态为 preview_ready
    5. 保存编辑历史
    """
```

### 4.3 finalize_worker.py

```python
"""Worker: finalize 任务"""

def process_finalize_task(task_id: str, work_dir: str, output_mode: str):
    """
    1. 下载必要产物（原视频、delay_cuts、pause_cuts_on_original）
    2. 如 output_mode='vertical_1080p'，先 normalize
    3. 调用 finalize_processor.run_finalize()
    4. 上传产物到 TOS
    5. 更新任务状态为 success
    """
```

---

## 第五部分：实施步骤

### Phase 1: online_version 基础模块（2 天）

1. 创建目录结构
2. 实现 `script_formatter.py`
3. 实现 `generate_audio_b.py`
4. 实现 `pause_mapping.py`（基于 TimelineMapper）

### Phase 2: 三阶段处理器（2-3 天）

1. 实现 `analyze_processor.py`
2. 实现 `preview_processor.py`
3. 实现 `finalize_processor.py`（含 normalize 逻辑）
4. 单元测试

### Phase 3: Worker 集成（2 天）

1. 实现三个 Worker
2. 集成测试

### Phase 4: 后端 API（2 天）

1. 数据库模型
2. API 路由
3. 状态机管理

### Phase 5: 前端（2-3 天）

1. 页面框架
2. 删除线编辑器（ranges 方案）
3. 三阶段交互

---

## 关键澄清

### 关于 TimelineMapper 的使用

`pause_mapping.py` 直接复用原代码 `time_mapping.py` 中的 `TimelineMapper` 类：

```python
from time_mapping import TimelineMapper

mapper = TimelineMapper(delay_cuts, original_duration)
mapper.build_timeline_a()
mapper.build_index_a()

# 将 pause_cut 从 Ta 映射到 T0
start_t0 = mapper.convert_ta_to_t0(pause['start_time'])
```

此方案已验证可行，`TimelineMapper` 提供完整的 `Ta → T0` 映射能力。

### 关于 audio_b 的定位

- **仅用于试听**，不用于最终视频生成
- 最终视频使用 `DirectCutter` 直接剪辑原视频
- 避免 audio_b → 最终视频 的时间轴二次映射复杂性
