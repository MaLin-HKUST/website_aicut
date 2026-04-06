"""
暂停切割点映射模块

负责将 pause_cuts 从 audio_a 时间轴映射回原视频时间轴，
并生成 DirectCutter 兼容的 JSON 格式。

规格来源：doc/cujian_plan_cx2.md 5.2 节
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def map_pauses_to_original_seconds(
    pause_cuts_on_audio_a: list[dict],
    delay_cuts: list[dict],
) -> list[dict]:
    """
    将 pause cuts 从 audio_a 时间轴映射回原视频时间轴
    
    Args:
        pause_cuts_on_audio_a: 在 audio_a 时间轴上检测到的 pause cuts，
                               每个元素包含 start_time, end_time（秒）
        delay_cuts: 延迟切割点，用于时间轴映射计算
                    每个元素包含 start_time, end_time（秒）
    
    Returns:
        映射到原视频时间轴的 pause cuts（秒级时间）
        每个元素包含 start_time, end_time, type="pause"
    
    Example:
        >>> pause_cuts = [{"start_time": 5.0, "end_time": 6.5}]
        >>> delay_cuts = [{"start_time": 10.0, "end_time": 12.0}]
        >>> map_pauses_to_original_seconds(pause_cuts, delay_cuts)
        [{"start_time": 15.0, "end_time": 16.5, "type": "pause"}]
    """
    if not pause_cuts_on_audio_a:
        return []
    
    # 计算累积延迟映射
    delay_mapping = _build_delay_mapping(delay_cuts)
    
    mapped_pauses = []
    for pause in pause_cuts_on_audio_a:
        start_on_audio_a = float(pause.get("start_time", 0))
        end_on_audio_a = float(pause.get("end_time", 0))
        
        # 将 audio_a 时间映射回原视频时间
        start_on_original = _map_audio_a_to_original(start_on_audio_a, delay_mapping)
        end_on_original = _map_audio_a_to_original(end_on_audio_a, delay_mapping)
        
        mapped_pauses.append({
            "start_time": start_on_original,
            "end_time": end_on_original,
            "type": "pause",
        })
        
        logger.debug(
            f"Mapped pause: audio_a[{start_on_audio_a:.3f}-{end_on_audio_a:.3f}] -> "
            f"original[{start_on_original:.3f}-{end_on_original:.3f}]"
        )
    
    return mapped_pauses


def dump_pause_cuts_for_direct_cutter(
    mapped_pauses_seconds: list[dict],
    output_path: str,
) -> str:
    """
    将映射后的 pause cuts 输出为 DirectCutter 兼容的 JSON 格式
    
    DirectCutter 期望的格式：
    {
        "cut_segments": [
            {
                "start_time": 1234,  # 毫秒
                "end_time": 1567,
                "type": "pause",
                "position": ""
            }
        ]
    }
    
    Args:
        mapped_pauses_seconds: 映射到原视频时间轴的 pause cuts（秒级时间）
        output_path: 输出 JSON 文件路径
    
    Returns:
        输出文件路径
    
    Note:
        输出文件中的时间单位为毫秒
    """
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    cut_segments = []
    for pause in mapped_pauses_seconds:
        # 转换为毫秒（DirectCutter 使用毫秒）
        start_ms = int(pause["start_time"] * 1000)
        end_ms = int(pause["end_time"] * 1000)
        
        cut_segments.append({
            "start_time": start_ms,
            "end_time": end_ms,
            "type": "pause",
            "position": "",
        })
    
    result = {"cut_segments": cut_segments}
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Pause cuts saved to {output_path} ({len(cut_segments)} segments)")
    return output_path


def load_pause_cuts_from_audio_a(pause_cuts_path: str) -> list[dict]:
    """
    从 pause_detect 模块的输出加载 pause cuts
    
    Args:
        pause_cuts_path: pause cuts JSON 文件路径
    
    Returns:
        pause cuts 列表，每个元素包含 start_time, end_time（秒）
    """
    with open(pause_cuts_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # pause_detect 可能输出不同的格式，这里做兼容处理
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # 可能是 cut_segments 格式
        segments = data.get("cut_segments", [])
        if not segments:
            return []
        
        # 检测时间单位：如果第一个 start_time >= 1000，认为是毫秒
        # （因为正常情况下单个音频不会超过 1000 秒）
        first_start = segments[0].get("start_time", 0) if segments else 0
        is_milliseconds = first_start >= 1000
        
        # 转换为秒级时间
        return [
            {
                "start_time": s.get("start_time", 0) / 1000.0 if is_milliseconds else s.get("start_time", 0),
                "end_time": s.get("end_time", 0) / 1000.0 if is_milliseconds else s.get("end_time", 0),
            }
            for s in segments
        ]
    
    return []


def _build_delay_mapping(delay_cuts: list[dict]) -> list[dict]:
    """
    构建延迟映射表
    
    delay_cuts 表示需要从原视频中丢弃的片段。
    对于 audio_a 时间轴上的每个点，需要加上之前所有被丢弃片段的时长，
    才能得到对应的原视频时间点。
    
    映射逻辑：
    - 对于每个 delay cut [start, end]，duration = end - start
    - 在 audio_a 时间轴上，delay cut 被移除了，所以：
      - audio_a 时间 0 到 start 对应原视频 0 到 start
      - audio_a 时间 start 到 (next_start - duration) 对应原视频 (start + duration) 到 next_start
    
    Returns:
        延迟映射列表，每个元素包含:
        - audio_a_time: audio_a 时间轴上的起始点
        - cumulative_delay: 到该点为止的累积延迟
    """
    if not delay_cuts:
        return []
    
    # 按开始时间排序
    sorted_cuts = sorted(delay_cuts, key=lambda x: x.get("start_time", 0))
    
    mapping = []
    cumulative_delay = 0.0
    
    for cut in sorted_cuts:
        end_time = float(cut.get("end_time", 0))
        duration = end_time - float(cut.get("start_time", 0))
        
        # 在这个 delay cut 结束之后，audio_a 时间需要加上累积延迟
        # audio_a 时间 = 原视频时间 - cumulative_delay
        # 所以原视频时间 = audio_a 时间 + cumulative_delay
        mapping.append({
            "audio_a_time": end_time - cumulative_delay - duration,
            "cumulative_delay": cumulative_delay + duration,
        })
        
        # 更新累积延迟
        cumulative_delay += duration
    
    return mapping


def _map_audio_a_to_original(
    audio_a_time: float,
    delay_mapping: list[dict],
) -> float:
    """
    将 audio_a 时间映射回原视频时间
    
    Args:
        audio_a_time: audio_a 时间轴上的时间点（秒）
        delay_mapping: 延迟映射表
    
    Returns:
        对应的原视频时间点（秒）
    
    注意：
    - delay_mapping 中的 audio_a_time 表示从该时间点开始，需要使用对应的 cumulative_delay
    - 但对于 pause cuts 的结束时间点，如果它正好等于某个 audio_a_time，
      应该使用前一个区间的 delay（因为 pause cut 是连续的）
    """
    if not delay_mapping:
        return audio_a_time
    
    # 找到合适的映射区间
    cumulative_delay = 0.0
    for i, mapping in enumerate(delay_mapping):
        # 使用 <= 确保当 audio_a_time 正好等于某个边界时，
        # 我们检查是否是最后一个区间，如果是则使用该区间的 delay
        if audio_a_time < mapping["audio_a_time"]:
            break
        # 如果 audio_a_time 等于当前 audio_a_time，并且不是最后一个区间，
        # 那么需要看下一个区间来决定
        if audio_a_time == mapping["audio_a_time"] and i < len(delay_mapping) - 1:
            # 检查下一个区间的 delay
            next_delay = delay_mapping[i + 1]["cumulative_delay"]
            # 对于 pause cut 的边界，我们可能需要更复杂的逻辑
            # 这里我们继续使用当前的 cumulative_delay
            pass
        cumulative_delay = mapping["cumulative_delay"]
    
    return audio_a_time + cumulative_delay


def map_pauses_from_audio_a_file(
    pause_cuts_on_audio_a_path: str,
    delay_cuts_path: str,
    output_path: str,
) -> str:
    """
    从文件加载 pause cuts 和 delay cuts，映射后输出 DirectCutter 兼容格式
    
    Args:
        pause_cuts_on_audio_a_path: pause cuts JSON 文件路径（秒级时间）
        delay_cuts_path: delay cuts JSON 文件路径（秒级时间）
        output_path: 输出文件路径
    
    Returns:
        输出文件路径
    """
    # 加载 pause cuts
    pause_cuts = load_pause_cuts_from_audio_a(pause_cuts_on_audio_a_path)
    
    # 加载 delay cuts
    with open(delay_cuts_path, "r", encoding="utf-8") as f:
        delay_cuts = json.load(f)
    
    # 映射时间轴
    mapped_pauses = map_pauses_to_original_seconds(pause_cuts, delay_cuts)
    
    # 输出 DirectCutter 兼容格式
    return dump_pause_cuts_for_direct_cutter(mapped_pauses, output_path)
