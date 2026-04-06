"""
Analyze 阶段处理器

职责：
1. 从 TOS 下载原视频和标准文案
2. 执行 A 流程（run_raw_cut.py --flow-a）
3. 产出 script、ASR、DelayCuts、audio_a

规格来源：doc/cujian_plan_cx2.md 4.1 节
"""

import json
import logging
import subprocess
from pathlib import Path

from .paths import RUN_RAW_CUT, ensure_task_dirs

logger = logging.getLogger(__name__)


def process_analyze(
    task_id: str,
    original_video_path: str,
    reference_text_path: str,
    output_dir: str | None = None,
    task_prefix: str | None = None,
) -> dict:
    """
    执行 Analyze 阶段处理
    
    Args:
        task_id: 任务 ID
        original_video_path: 原视频本地路径
        reference_text_path: 标准文案本地路径
        output_dir: 输出目录，默认为 /data/smart-cut/{task_id}/analyze
        task_prefix: 输出文件前缀，默认为 task_{task_id}
    
    Returns:
        产物信息字典
    
    Raises:
        FileNotFoundError: 当输入文件不存在时
        RuntimeError: 当 run_raw_cut 执行失败时
    """
    # 参数处理
    output_dir = output_dir or str(ensure_task_dirs(task_id)["analyze"])
    task_prefix = task_prefix or f"task_{task_id}"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 验证输入文件
    if not Path(original_video_path).exists():
        raise FileNotFoundError(f"原视频文件不存在: {original_video_path}")
    if not Path(reference_text_path).exists():
        raise FileNotFoundError(f"标准文案文件不存在: {reference_text_path}")
    
    logger.info(f"Starting analyze for task {task_id}")
    logger.info(f"Video: {original_video_path}")
    logger.info(f"Reference: {reference_text_path}")
    logger.info(f"Output dir: {output_dir}")
    
    # 构建命令
    cmd = [
        "python",
        str(RUN_RAW_CUT),
        "-i", original_video_path,
        "-r", reference_text_path,
        "-o", output_dir,
        "-n", task_prefix,
        "--flow-a",
    ]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stderr:
            logger.debug(f"run_raw_cut stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        error_msg = f"run_raw_cut 执行失败: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    
    # 收集产物
    artifacts = _collect_artifacts(output_dir, task_prefix)
    
    # 读取 script 内容
    script_content = None
    if artifacts.get("script_path"):
        script_path = Path(artifacts["script_path"])
        if script_path.exists():
            script_content = script_path.read_text(encoding="utf-8")
    
    result_dict = {
        "task_id": task_id,
        "output_dir": output_dir,
        "script": script_content,
        "artifacts": artifacts,
    }
    
    logger.info(f"Analyze completed for task {task_id}")
    logger.info(f"Script length: {len(script_content) if script_content else 0}")
    
    return result_dict


def _collect_artifacts(output_dir: str, task_prefix: str) -> dict:
    """
    收集 A 流程产物
    
    Args:
        output_dir: 输出目录
        task_prefix: 文件前缀
    
    Returns:
        产物路径字典
    """
    output_path = Path(output_dir)
    
    # 构建预期文件路径
    artifacts = {
        "asr_result": output_path / f"{task_prefix}_ASR.Result.json",
        "original_text": output_path / f"{task_prefix}_原文.TXT",
        "script": output_path / f"{task_prefix}_Script1.txt",
        "delay_cuts": output_path / f"{task_prefix}_DelayCutSegments.json",
        "audio_a": output_path / f"{task_prefix}_audio_a.mp3",
    }
    
    # 检查文件存在性并收集路径
    result = {}
    for key, path in artifacts.items():
        if path.exists():
            result[f"{key}_path"] = str(path)
            logger.debug(f"Found artifact: {key} -> {path}")
        else:
            # 尝试查找类似文件
            pattern = f"{task_prefix}_{key.upper() if key != 'script' else 'Script'}"
            matches = list(output_path.glob(f"{task_prefix}*"))
            for m in matches:
                if key in m.name.lower() or (key == "script" and "Script" in m.name):
                    result[f"{key}_path"] = str(m)
                    logger.debug(f"Found artifact (pattern match): {key} -> {m}")
                    break
    
    return result


def get_delete_ranges_from_script(script: str) -> list[dict]:
    """
    从 script 提取删除范围（用于前端展示）
    
    Args:
        script: 大括号格式的 script
    
    Returns:
        删除范围列表
    """
    from .script_formatter import script_to_delete_ranges
    return script_to_delete_ranges(script)


def analyze_pipeline(
    task_id: str,
    original_video_url: str,
    reference_text_url: str,
    download_fn: callable,
) -> dict:
    """
    Analyze 阶段完整流程
    
    Args:
        task_id: 任务 ID
        original_video_url: 原视频 TOS URL
        reference_text_url: 标准文案 TOS URL
        download_fn: 下载函数，接收 (url, local_path) 返回 local_path
    
    Returns:
        处理结果字典
    """
    # 准备目录
    dirs = ensure_task_dirs(task_id)
    input_dir = dirs["input"]
    analyze_dir = dirs["analyze"]
    
    # 下载输入文件
    video_path = input_dir / "source_video.mp4"
    reference_path = input_dir / "reference.txt"
    
    logger.info(f"Downloading inputs for task {task_id}")
    download_fn(original_video_url, str(video_path))
    download_fn(reference_text_url, str(reference_path))
    
    # 执行 analyze
    result = process_analyze(
        task_id=task_id,
        original_video_path=str(video_path),
        reference_text_path=str(reference_path),
        output_dir=str(analyze_dir),
    )
    
    return result
