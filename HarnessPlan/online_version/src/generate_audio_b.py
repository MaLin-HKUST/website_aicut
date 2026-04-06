"""
音频 B 生成模块

基于延迟切割点生成试听音频 B，使用 FFmpeg filter_complex 一次性重编码输出。
音频 B 仅用于试听，不参与最终视频合成。

规格来源：doc/cujian_plan_cx2.md 5.1 节
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


def generate_audio_b(
    audio_a_path: str,
    delay_cuts: List[Dict[str, Any]],
    output_path: str
) -> str:
    """
    基于延迟切割点生成试听音频 B

    实现原则：
    - audio_b 只用于试听，不要求映射回原视频
    - 优先保证试听边界稳定，不追求无损 copy
    - 统一用一次 filter_complex 重编码输出，避免边界不准和时长漂移

    Args:
        audio_a_path: audio_a.mp3 路径
        delay_cuts: 延迟切割点列表，每个元素包含 start_time, end_time 等字段
                   表示需要丢弃的片段，其余部分需要保留
        output_path: 输出 audio_b.mp3 路径

    Returns:
        输出文件路径

    Raises:
        FileNotFoundError: 当输入音频文件不存在时
        ValueError: 当 delay_cuts 格式无效时
        RuntimeError: 当 FFmpeg 执行失败时

    Example:
        >>> delay_cuts = [
        ...     {"start_time": 5.0, "end_time": 8.0, "type": "discard"},
        ...     {"start_time": 15.0, "end_time": 18.0, "type": "discard"},
        ... ]
        >>> generate_audio_b("audio_a.mp3", delay_cuts, "audio_b.mp3")
        "audio_b.mp3"
    """
    audio_a_path_obj = Path(audio_a_path)
    if not audio_a_path_obj.exists():
        raise FileNotFoundError(f"输入音频文件不存在: {audio_a_path}")

    # 确保输出目录存在
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # 获取音频总时长
    duration = _get_audio_duration(audio_a_path)
    logger.info(f"音频总时长: {duration:.3f}s, 输入: {audio_a_path}")

    # 计算需要保留的片段
    keep_segments = _calculate_keep_segments(delay_cuts, duration)
    logger.info(f"保留片段数: {len(keep_segments)}")

    if not keep_segments:
        logger.warning("没有需要保留的片段，生成空音频")
        _generate_silent_audio(output_path, duration=0.1)
        return str(output_path_obj.absolute())

    # 构建并执行 FFmpeg 命令
    _run_ffmpeg_concat(audio_a_path, keep_segments, output_path)

    logger.info(f"音频 B 生成成功: {output_path}")
    return str(output_path_obj.absolute())


def _get_audio_duration(audio_path: str) -> float:
    """
    获取音频文件时长（秒）

    Args:
        audio_path: 音频文件路径

    Returns:
        音频时长（秒）

    Raises:
        RuntimeError: 当 ffprobe 执行失败时
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        duration_str = result.stdout.strip()
        if not duration_str:
            raise RuntimeError(f"无法获取音频时长: {audio_path}")
        return float(duration_str)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe 执行失败: {e.stderr}") from e
    except ValueError as e:
        raise RuntimeError(f"解析音频时长失败: {e}") from e


def _calculate_keep_segments(
    delay_cuts: List[Dict[str, Any]],
    total_duration: float,
) -> List[Dict[str, float]]:
    """
    根据 delay_cuts 计算需要保留的片段

    delay_cuts 表示需要丢弃的片段（discard），其余部分需要保留。
    假设 delay_cuts 中的时间戳是相对于 audio_a 时间轴的秒级时间。

    Args:
        delay_cuts: 延迟切割点列表，每个元素包含 start_time, end_time 字段
        total_duration: 音频总时长（秒）

    Returns:
        保留片段列表，每个元素包含 start, end 字段（秒）

    Raises:
        ValueError: 当 delay_cuts 格式无效时
    """
    if not delay_cuts:
        # 没有切割点，保留整个音频
        return [{"start": 0.0, "end": total_duration}]

    # 验证并提取切割点
    discard_segments = []
    for i, cut in enumerate(delay_cuts):
        if "start_time" not in cut or "end_time" not in cut:
            raise ValueError(
                f"delay_cuts[{i}] 格式错误: 缺少 start_time 或 end_time 字段"
            )

        start_time = float(cut["start_time"])
        end_time = float(cut["end_time"])

        if start_time < 0 or end_time < 0:
            raise ValueError(
                f"delay_cuts[{i}] 时间值无效: start_time={start_time}, end_time={end_time}"
            )

        if start_time >= end_time:
            # 跳过无效的切割点
            logger.warning(
                f"跳过无效的切割点[{i}]: start_time={start_time} >= end_time={end_time}"
            )
            continue

        discard_segments.append({
            "start": max(0.0, start_time),
            "end": min(end_time, total_duration),
        })

    if not discard_segments:
        # 没有有效的丢弃片段，保留整个音频
        return [{"start": 0.0, "end": total_duration}]

    # 按开始时间排序
    discard_segments.sort(key=lambda x: x["start"])

    # 合并重叠的丢弃片段
    merged_discards = [discard_segments[0]]
    for segment in discard_segments[1:]:
        last = merged_discards[-1]
        if segment["start"] <= last["end"]:
            # 重叠或相邻，合并
            last["end"] = max(last["end"], segment["end"])
        else:
            merged_discards.append(segment)

    # 计算保留片段（丢弃片段之间的部分）
    keep_segments = []
    current_pos = 0.0

    for discard in merged_discards:
        if current_pos < discard["start"]:
            # 当前位置到丢弃片段开始之间有保留内容
            keep_segments.append({
                "start": current_pos,
                "end": discard["start"],
            })
        # 跳过丢弃片段
        current_pos = max(current_pos, discard["end"])

    # 处理最后一个丢弃片段之后的部分
    if current_pos < total_duration:
        keep_segments.append({
            "start": current_pos,
            "end": total_duration,
        })

    return keep_segments


def _build_filter_complex(
    keep_segments: List[Dict[str, float]],
) -> str:
    """
    构建 FFmpeg filter_complex 表达式

    使用 atrim 提取各段，然后用 concat 拼接。
    格式: [0:a]atrim=start=0:end=5[a0];[0:a]atrim=start=10:end=15[a1];[a0][a1]concat=n=2:v=0:a=1[out]

    Args:
        keep_segments: 保留片段列表

    Returns:
        filter_complex 表达式字符串
    """
    if len(keep_segments) == 1:
        # 单段直接裁剪
        seg = keep_segments[0]
        return f"[0:a]atrim=start={seg['start']}:end={seg['end']}[out]"

    # 多段拼接
    filters = []
    labels = []

    for i, seg in enumerate(keep_segments):
        label = f"[a{i}]"
        labels.append(label)
        filters.append(
            f"[0:a]atrim=start={seg['start']}:end={seg['end']}{label}"
        )

    # concat 过滤器
    concat_labels = "".join(labels)
    filters.append(
        f"{concat_labels}concat=n={len(keep_segments)}:v=0:a=1[out]"
    )

    return ";".join(filters)


def _run_ffmpeg_concat(
    audio_a_path: str,
    keep_segments: List[Dict[str, float]],
    output_path: str,
) -> None:
    """
    执行 FFmpeg 命令拼接音频片段

    使用 filter_complex 一次性重编码输出，避免边界不准和时长漂移。

    Args:
        audio_a_path: 输入音频路径
        keep_segments: 保留片段列表
        output_path: 输出音频路径

    Raises:
        RuntimeError: 当 FFmpeg 执行失败时
    """
    filter_complex = _build_filter_complex(keep_segments)

    cmd = [
        "ffmpeg",
        "-y",  # 覆盖输出文件
        "-hide_banner",
        "-loglevel", "warning",
        "-i", audio_a_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "mp3",
        "-q:a", "4",  # VBR 质量，4 是较好的平衡点
        output_path,
    ]

    logger.debug(f"FFmpeg 命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stderr:
            logger.debug(f"FFmpeg stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg 执行失败: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def _generate_silent_audio(output_path: str, duration: float = 0.1) -> None:
    """
    生成静音音频（用于边界情况）

    Args:
        output_path: 输出音频路径
        duration: 静音时长（秒）

    Raises:
        RuntimeError: 当 FFmpeg 执行失败时
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "warning",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration),
        "-c:a", "mp3",
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"生成静音音频失败: {e.stderr}") from e


def generate_audio_b_with_cuts(
    audio_a_path: str,
    keep_segments: List[Dict[str, float]],
    output_path: str,
) -> str:
    """
    直接使用保留片段列表生成音频 B（高级用法）

    Args:
        audio_a_path: audio_a.mp3 路径
        keep_segments: 保留片段列表，每个元素包含 start, end 字段（秒）
        output_path: 输出 audio_b.mp3 路径

    Returns:
        输出文件路径
    """
    audio_a_path_obj = Path(audio_a_path)
    if not audio_a_path_obj.exists():
        raise FileNotFoundError(f"输入音频文件不存在: {audio_a_path}")

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    if not keep_segments:
        logger.warning("没有需要保留的片段，生成空音频")
        _generate_silent_audio(output_path, duration=0.1)
        return str(output_path_obj.absolute())

    _run_ffmpeg_concat(audio_a_path, keep_segments, output_path)

    logger.info(f"音频 B 生成成功: {output_path}")
    return str(output_path_obj.absolute())
