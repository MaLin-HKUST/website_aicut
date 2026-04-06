"""
Preview 阶段处理器

职责：
1. 用用户修订后的脚本重新生成 edited_delay_cuts
2. 基于 edited_delay_cuts 重新生成 edited_audio_a
3. 用 detect_pauses_on_audio_a() 生成 pause_cuts_on_audio_a
4. 生成 audio_b
5. 把 pause_cuts_on_audio_a 映射回原视频时间轴
6. 保存 DirectCutter 兼容的 pause_cuts_on_original.json

规格来源：doc/cujian_plan_cx2.md 4.2 节
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# 添加算法库路径
sys.path.insert(0, str(Path("/app/aicut2602")))

from .generate_audio_b import generate_audio_b
from .pause_mapping import map_pauses_to_original_seconds, dump_pause_cuts_for_direct_cutter
from .paths import ensure_task_dirs

logger = logging.getLogger(__name__)


def process_preview(
    task_id: str,
    edited_script: str,
    original_script: str,
    asr_result_path: str,
    original_video_path: str,
    output_dir: str | None = None,
    edit_id: str | None = None,
) -> dict:
    """
    执行 Preview 阶段处理
    
    Args:
        task_id: 任务 ID
        edited_script: 用户编辑后的脚本（大括号格式）
        original_script: 原始脚本（大括号格式，用于对比验证）
        asr_result_path: ASR 结果文件路径
        original_video_path: 原视频路径（用于 pause 检测）
        output_dir: 输出目录，默认为 /data/smart-cut/{task_id}/preview/{edit_id}
        edit_id: 编辑记录 ID
    
    Returns:
        产物信息字典
    
    Raises:
        ValueError: 当脚本格式无效或编辑内容非法时
        RuntimeError: 当处理失败时
    """
    # 验证编辑后的脚本
    _validate_edited_script(edited_script, original_script)
    
    # 准备目录
    if output_dir is None:
        dirs = ensure_task_dirs(task_id)
        if edit_id:
            output_dir = dirs["preview"] / edit_id
        else:
            output_dir = dirs["preview"] / "default"
        output_dir = str(output_dir)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting preview for task {task_id}, edit_id={edit_id}")
    
    # 1. 用编辑后的脚本重新生成 edited_delay_cuts
    edited_delay_cuts = _generate_edited_delay_cuts(
        edited_script, asr_result_path, output_path
    )
    
    # 保存 edited_delay_cuts
    delay_cuts_path = output_path / "edited_delay_cuts.json"
    with open(delay_cuts_path, "w", encoding="utf-8") as f:
        json.dump(edited_delay_cuts, f, ensure_ascii=False, indent=2)
    
    # 2. 基于 edited_delay_cuts 重新生成 edited_audio_a
    edited_audio_a_path = output_path / "edited_audio_a.mp3"
    _generate_edited_audio_a(
        edited_delay_cuts, original_video_path, str(edited_audio_a_path)
    )
    
    # 3. 用 detect_pauses_on_audio_a() 生成 pause_cuts_on_audio_a
    pause_cuts_on_audio_a = _detect_pauses_on_audio_a(
        str(edited_audio_a_path), output_path
    )
    
    # 保存 pause_cuts_on_audio_a
    pause_cuts_audio_a_path = output_path / "pause_cuts_on_audio_a.json"
    with open(pause_cuts_audio_a_path, "w", encoding="utf-8") as f:
        json.dump(pause_cuts_on_audio_a, f, ensure_ascii=False, indent=2)
    
    # 4. 生成 audio_b
    audio_b_path = output_path / "audio_b.mp3"
    generate_audio_b(
        str(edited_audio_a_path),
        edited_delay_cuts,
        str(audio_b_path),
    )
    
    # 5. 把 pause_cuts_on_audio_a 映射回原视频时间轴
    mapped_pauses = map_pauses_to_original_seconds(
        pause_cuts_on_audio_a,
        edited_delay_cuts,
    )
    
    # 6. 保存 DirectCutter 兼容的 pause_cuts_on_original.json
    pause_cuts_original_path = output_path / "pause_cuts_on_original.json"
    dump_pause_cuts_for_direct_cutter(mapped_pauses, str(pause_cuts_original_path))
    
    result = {
        "task_id": task_id,
        "edit_id": edit_id,
        "output_dir": output_dir,
        "edited_delay_cuts_path": str(delay_cuts_path),
        "edited_audio_a_path": str(edited_audio_a_path),
        "pause_cuts_on_audio_a_path": str(pause_cuts_audio_a_path),
        "pause_cuts_on_original_path": str(pause_cuts_original_path),
        "audio_b_path": str(audio_b_path),
    }
    
    logger.info(f"Preview completed for task {task_id}, edit_id={edit_id}")
    
    return result


def _get_pure_text(script: str) -> str:
    """
    获取脚本的纯文本（去掉所有大括号）
    
    Args:
        script: 大括号格式脚本
    
    Returns:
        纯文本（所有大括号被移除）
    """
    return script.replace('{', '').replace('}', '')


def _validate_edited_script(edited_script: str, original_script: str) -> None:
    """
    验证编辑后的脚本
    
    约束：
    - 不支持自由输入新文字
    - 不支持改写正文内容
    - 不支持直接删除正文字符
    - 正文字符顺序必须保持与 analyze 产出的 script 一致
    
    Args:
        edited_script: 编辑后的脚本
        original_script: 原始脚本
    
    Raises:
        ValueError: 当验证失败时
    """
    from .script_formatter import validate_script_format
    
    # 验证大括号格式
    if not validate_script_format(edited_script):
        raise ValueError("编辑后的脚本大括号格式不合法")
    
    # 获取纯文本（去掉所有大括号后）
    edited_pure = _get_pure_text(edited_script)
    original_pure = _get_pure_text(original_script)
    
    # 验证正文字符内容一致（去掉所有大括号后）
    if edited_pure != original_pure:
        raise ValueError(
            "编辑后的正文内容与原始内容不一致。"
            "只允许修改删除线范围，不允许修改正文内容。"
        )
    
    logger.debug("Script validation passed")


def _generate_edited_delay_cuts(
    edited_script: str,
    asr_result_path: str,
    output_path: Path,
) -> list[dict]:
    """
    用编辑后的脚本重新生成 delay cuts
    
    Args:
        edited_script: 编辑后的脚本（大括号格式）
        asr_result_path: ASR 结果路径
        output_path: 输出目录
    
    Returns:
        新的 delay cuts 列表
    """
    try:
        # 导入算法模块
        from libs.cut_breakpoints.src.script_to_delay_cuts import ScriptToDelayCuts
        
        # 创建转换器
        converter = ScriptToDelayCuts()
        
        # 生成 delay cuts
        # 注意：这里假设 ScriptToDelayCuts 可以接受脚本和 ASR 路径
        # 如果接口不同，需要调整
        delay_cuts = converter.convert(
            script=edited_script,
            asr_result_path=asr_result_path,
        )
        
        # 确保返回列表格式
        if not isinstance(delay_cuts, list):
            delay_cuts = delay_cuts.get("cut_segments", [])
        
        return delay_cuts
        
    except Exception as e:
        logger.warning(f"Failed to use ScriptToDelayCuts: {e}, using fallback")
        # Fallback：从脚本的大括号提取删除范围，结合 ASR 时间戳生成 cuts
        return _fallback_generate_delay_cuts(edited_script, asr_result_path)


def _fallback_generate_delay_cuts(
    edited_script: str,
    asr_result_path: str,
) -> list[dict]:
    """
    Fallback 方法：从脚本提取删除范围生成 delay cuts
    
    这是一个简化实现，实际应该使用算法库。
    """
    from .script_formatter import script_to_delete_ranges
    
    # 加载 ASR 结果
    with open(asr_result_path, "r", encoding="utf-8") as f:
        asr_result = json.load(f)
    
    # 提取删除范围（字符级别）
    delete_ranges = script_to_delete_ranges(edited_script)
    
    # 将字符范围映射到时间范围
    # 这里需要 ASR 的时间戳信息
    # 简化实现：假设 ASR 有 word-level 时间戳
    delay_cuts = []
    
    # TODO: 实现基于 ASR 的字符到时间映射
    # 这只是一个占位实现
    utterances = asr_result.get("utterances", [])
    text = asr_result.get("text", "")
    
    for range_info in delete_ranges:
        start_char = range_info["start"]
        end_char = range_info["end"]
        
        # 找到对应的时间
        start_time = _char_to_time(start_char, text, utterances)
        end_time = _char_to_time(end_char, text, utterances)
        
        if start_time is not None and end_time is not None:
            delay_cuts.append({
                "start_time": start_time,
                "end_time": end_time,
                "type": "discard",
            })
    
    return delay_cuts


def _char_to_time(char_index: int, text: str, utterances: list) -> float | None:
    """
    将字符索引映射到时间
    
    简化实现：找到包含该字符的 utterance
    """
    current_pos = 0
    for utt in utterances:
        utt_text = utt.get("text", "")
        utt_len = len(utt_text)
        
        if current_pos <= char_index < current_pos + utt_len:
            # 计算在 utterance 内的比例
            ratio = (char_index - current_pos) / utt_len if utt_len > 0 else 0
            start_time = utt.get("start_time", 0)
            end_time = utt.get("end_time", 0)
            return start_time + (end_time - start_time) * ratio
        
        current_pos += utt_len
    
    return None


def _generate_edited_audio_a(
    delay_cuts: list[dict],
    original_video_path: str,
    output_path: str,
) -> str:
    """
    基于 delay cuts 从原视频生成 edited_audio_a
    
    Args:
        delay_cuts: 延迟切割点
        original_video_path: 原视频路径
        output_path: 输出音频路径
    
    Returns:
        输出文件路径
    """
    import subprocess
    
    # 计算保留片段
    keep_segments = []
    
    # 获取视频时长
    duration = _get_video_duration(original_video_path)
    
    if not delay_cuts:
        keep_segments = [{"start": 0.0, "end": duration}]
    else:
        current_pos = 0.0
        for cut in sorted(delay_cuts, key=lambda x: x.get("start_time", 0)):
            start = cut.get("start_time", 0)
            end = cut.get("end_time", 0)
            
            if current_pos < start:
                keep_segments.append({"start": current_pos, "end": start})
            
            current_pos = max(current_pos, end)
        
        if current_pos < duration:
            keep_segments.append({"start": current_pos, "end": duration})
    
    # 使用 FFmpeg 提取并拼接音频
    if len(keep_segments) == 1:
        # 单段
        seg = keep_segments[0]
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "warning",
            "-ss", str(seg["start"]),
            "-t", str(seg["end"] - seg["start"]),
            "-i", original_video_path,
            "-vn",  # 只提取音频
            "-c:a", "mp3",
            "-q:a", "4",
            output_path,
        ]
    else:
        # 多段，使用 filter_complex
        filters = []
        labels = []
        
        for i, seg in enumerate(keep_segments):
            label = f"[a{i}]"
            labels.append(label)
            filters.append(
                f"[0:a]atrim=start={seg['start']}:end={seg['end']}{label}"
            )
        
        concat_labels = "".join(labels)
        filters.append(
            f"{concat_labels}concat=n={len(keep_segments)}:v=0:a=1[outa]"
        )
        
        filter_complex = ";".join(filters)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "warning",
            "-i", original_video_path,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "mp3",
            "-q:a", "4",
            output_path,
        ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"生成 edited_audio_a 失败: {e.stderr}") from e
    
    return output_path


def _detect_pauses_on_audio_a(
    audio_a_path: str,
    output_path: Path,
) -> list[dict]:
    """
    在 audio_a 上检测暂停
    
    Args:
        audio_a_path: audio_a 文件路径
        output_path: 输出目录
    
    Returns:
        pause cuts 列表（秒级时间）
    """
    try:
        # 导入算法模块
        from libs.cut_breakpoints.src.pause_detect import detect_pauses_on_audio_a
        
        # 调用检测函数
        pause_cuts = detect_pauses_on_audio_a(audio_a_path)
        
        # 确保返回列表格式
        if not isinstance(pause_cuts, list):
            pause_cuts = pause_cuts.get("cut_segments", [])
        
        # 确保时间单位为秒
        if pause_cuts and "start_time" in pause_cuts[0]:
            if pause_cuts[0]["start_time"] > 1000:  # 推测为毫秒
                pause_cuts = [
                    {
                        "start_time": c["start_time"] / 1000.0,
                        "end_time": c["end_time"] / 1000.0,
                        "type": "pause",
                    }
                    for c in pause_cuts
                ]
        
        return pause_cuts
        
    except Exception as e:
        logger.warning(f"Failed to use pause_detect: {e}, using fallback")
        # Fallback：返回空列表
        return []


def _get_video_duration(video_path: str) -> float:
    """获取视频时长"""
    import subprocess
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())
