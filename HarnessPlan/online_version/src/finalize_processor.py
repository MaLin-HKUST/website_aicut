"""
Finalize 阶段处理器

职责：
1. 基于最后一次成功 preview 的产物生成最终视频
2. 支持两种输出模式：original / vertical_1080p
3. vertical_1080p 模式需要先调用 normalize_input_video
4. 输出码率遵循 min(input_bitrate, 12Mbps)

规格来源：doc/cujian_plan_cx2.md 4.3 节
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# 添加算法库路径
sys.path.insert(0, str(Path("/app/aicut2602")))

from .final_video_cutter import OnlineFinalVideoCutter, calculate_output_bitrate
from .paths import ensure_task_dirs

logger = logging.getLogger(__name__)


class OutputMode:
    """输出模式常量"""
    ORIGINAL = "original"
    VERTICAL_1080P = "vertical_1080p"


def process_finalize(
    task_id: str,
    original_video_path: str,
    edited_delay_cuts_path: str,
    pause_cuts_on_original_path: str,
    output_mode: str = OutputMode.ORIGINAL,
    output_dir: str | None = None,
    task_prefix: str | None = None,
) -> dict:
    """
    执行 Finalize 阶段处理
    
    Args:
        task_id: 任务 ID
        original_video_path: 原视频本地路径
        edited_delay_cuts_path: 编辑后的 delay cuts JSON 路径
        pause_cuts_on_original_path: pause cuts JSON 路径（DirectCutter 格式）
        output_mode: 输出模式，original 或 vertical_1080p
        output_dir: 输出目录，默认为 /data/smart-cut/{task_id}/final
        task_prefix: 文件前缀
    
    Returns:
        产物信息字典
    
    Raises:
        ValueError: 当参数无效时
        RuntimeError: 当处理失败时
    """
    # 参数验证
    if output_mode not in (OutputMode.ORIGINAL, OutputMode.VERTICAL_1080P):
        raise ValueError(f"无效的输出模式: {output_mode}")
    
    # 准备目录
    if output_dir is None:
        dirs = ensure_task_dirs(task_id)
        output_dir = dirs["final"]
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    task_prefix = task_prefix or f"task_{task_id}"
    
    logger.info(f"Starting finalize for task {task_id}, mode={output_mode}")
    
    # 确定视频源
    video_source_path = original_video_path
    normalized_video_path = None
    normalized_process_path = None
    
    # 如果是 vertical_1080p 模式，先执行 normalize
    if output_mode == OutputMode.VERTICAL_1080P:
        normalized_video_path, normalized_process_path = _normalize_video(
            original_video_path,
            output_path,
            task_prefix,
        )
        video_source_path = normalized_video_path
    
    # 获取输入视频码率
    input_bitrate = _get_video_bitrate(video_source_path)
    output_bitrate = calculate_output_bitrate(input_bitrate)
    
    logger.info(f"Input bitrate: {input_bitrate}, Output bitrate: {output_bitrate}")
    
    # 使用 OnlineFinalVideoCutter 执行切割
    cutter = OnlineFinalVideoCutter(video_source_path)
    cutter.load_delay_cuts(edited_delay_cuts_path)
    cutter.load_pause_cuts(pause_cuts_on_original_path)
    cutter.calculate_keep_segments()
    
    # 保存切割计划
    cut_plan_path = output_path / f"{task_prefix}_cut_plan.json"
    cutter.save_cut_plan(str(cut_plan_path))
    
    # 输出最终视频
    final_video_path = output_path / f"{task_prefix}_final_video.mp4"
    cutter.cut(
        str(final_video_path),
        video_bitrate=output_bitrate,
        maxrate=output_bitrate,
        bufsize=output_bitrate * 2,
        preset="veryfast",
        audio_bitrate="192k",
    )
    
    # 构建返回结果
    result = {
        "task_id": task_id,
        "output_mode": output_mode,
        "final_video_path": str(final_video_path),
        "cut_plan_path": str(cut_plan_path),
        "encoding_params": {
            "input_bitrate": input_bitrate,
            "output_bitrate": output_bitrate,
            "maxrate": output_bitrate,
            "bufsize": output_bitrate * 2,
            "mode": output_mode,
        },
    }
    
    # 如果是 vertical_1080p 模式，添加 normalize 产物信息
    if output_mode == OutputMode.VERTICAL_1080P:
        result["normalized_video_path"] = normalized_video_path
        result["normalized_process_path"] = normalized_process_path
    
    logger.info(f"Finalize completed for task {task_id}")
    logger.info(f"Final video: {final_video_path}")
    
    return result


def _normalize_video(
    original_video_path: str,
    output_dir: Path,
    task_prefix: str,
) -> tuple[str, str]:
    """
    执行视频归一化
    
    Args:
        original_video_path: 原视频路径
        output_dir: 输出目录
        task_prefix: 文件前缀
    
    Returns:
        (归一化视频路径, 处理记录路径)
    """
    try:
        # 导入算法模块
        from libs.cut_breakpoints.src.run_raw_cut import normalize_input_video
        
        normalized_video_path = output_dir / f"{task_prefix}_normalized_input.mp4"
        normalized_process_path = output_dir / f"{task_prefix}_normalized_input.process.json"
        
        logger.info(f"Normalizing video: {original_video_path}")
        
        # 调用 normalize 函数
        normalize_input_video(
            input_path=original_video_path,
            output_path=str(normalized_video_path),
            process_info_path=str(normalized_process_path),
        )
        
        logger.info(f"Normalization completed: {normalized_video_path}")
        
        return str(normalized_video_path), str(normalized_process_path)
        
    except Exception as e:
        logger.warning(f"Failed to use normalize_input_video: {e}")
        # Fallback：使用 ffmpeg 手动归一化
        return _fallback_normalize_video(original_video_path, output_dir, task_prefix)


def _fallback_normalize_video(
    original_video_path: str,
    output_dir: Path,
    task_prefix: str,
) -> tuple[str, str]:
    """
    Fallback 归一化实现
    
    使用 FFmpeg 将视频转换为 1080P 竖屏格式。
    """
    import subprocess
    
    normalized_video_path = output_dir / f"{task_prefix}_normalized_input.mp4"
    normalized_process_path = output_dir / f"{task_prefix}_normalized_input.process.json"
    
    # 使用 FFmpeg 进行归一化
    # 目标：1080P 竖屏 (1080x1920)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "warning",
        "-i", original_video_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        str(normalized_video_path),
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"视频归一化失败: {e.stderr}") from e
    
    # 保存处理信息
    process_info = {
        "input_path": original_video_path,
        "output_path": str(normalized_video_path),
        "operation": "normalize_to_1080p_vertical",
        "target_resolution": [1080, 1920],
    }
    
    with open(normalized_process_path, "w", encoding="utf-8") as f:
        json.dump(process_info, f, ensure_ascii=False, indent=2)
    
    return str(normalized_video_path), str(normalized_process_path)


def _get_video_bitrate(video_path: str) -> int | None:
    """
    获取视频码率
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        码率（bps），如果无法获取则返回 None
    """
    import subprocess
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        bitrate_str = result.stdout.strip()
        if bitrate_str and bitrate_str.isdigit():
            return int(bitrate_str)
    except Exception as e:
        logger.warning(f"Failed to get video bitrate: {e}")
    
    return None


def finalize_pipeline(
    task_id: str,
    original_video_url: str,
    edited_delay_cuts_url: str,
    pause_cuts_on_original_url: str,
    output_mode: str,
    download_fn: callable,
    upload_fn: callable,
) -> dict:
    """
    Finalize 阶段完整流程
    
    Args:
        task_id: 任务 ID
        original_video_url: 原视频 TOS URL
        edited_delay_cuts_url: delay cuts TOS URL
        pause_cuts_on_original_url: pause cuts TOS URL
        output_mode: 输出模式
        download_fn: 下载函数，接收 (url, local_path) 返回 local_path
        upload_fn: 上传函数，接收 (local_path, object_key) 返回 url
    
    Returns:
        处理结果字典
    """
    # 准备目录
    dirs = ensure_task_dirs(task_id)
    final_dir = dirs["final"]
    
    # 下载输入文件
    video_path = final_dir / "source_video.mp4"
    delay_cuts_path = final_dir / "edited_delay_cuts.json"
    pause_cuts_path = final_dir / "pause_cuts_on_original.json"
    
    logger.info(f"Downloading inputs for finalize, task {task_id}")
    download_fn(original_video_url, str(video_path))
    download_fn(edited_delay_cuts_url, str(delay_cuts_path))
    download_fn(pause_cuts_on_original_url, str(pause_cuts_path))
    
    # 执行 finalize
    result = process_finalize(
        task_id=task_id,
        original_video_path=str(video_path),
        edited_delay_cuts_path=str(delay_cuts_path),
        pause_cuts_on_original_path=str(pause_cuts_path),
        output_mode=output_mode,
        output_dir=str(final_dir),
    )
    
    # 上传最终视频
    final_video_path = result["final_video_path"]
    object_key = f"smart-cut/{task_id}/final_video.mp4"
    final_video_url = upload_fn(final_video_path, object_key)
    
    result["final_video_url"] = final_video_url
    
    # 上传其他产物
    if result.get("normalized_video_path"):
        norm_path = result["normalized_video_path"]
        norm_key = f"smart-cut/{task_id}/normalized_input.mp4"
        result["normalized_video_url"] = upload_fn(norm_path, norm_key)
    
    if result.get("normalized_process_path"):
        proc_path = result["normalized_process_path"]
        proc_key = f"smart-cut/{task_id}/normalized_input.process.json"
        result["normalized_process_url"] = upload_fn(proc_path, proc_key)
    
    cut_plan_path = result["cut_plan_path"]
    cut_plan_key = f"smart-cut/{task_id}/cut_plan.json"
    result["cut_plan_url"] = upload_fn(cut_plan_path, cut_plan_key)
    
    return result
