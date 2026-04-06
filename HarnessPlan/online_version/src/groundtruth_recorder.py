"""
GroundTruth 记录模块

负责将用户确认后的样本归档到 TOS，用于后续算法评测和回归测试。

规格来源：doc/cujian_plan_cx2.md 5.5 节
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import TOS_CUJIAN_INPUT_DATA_PREFIX

logger = logging.getLogger(__name__)


def record_groundtruth(
    task_id: str,
    company: str,
    reference_text: str,
    original_video_url: str,
    original_video_tos_key: str,
    asr_result: dict | str,
    analyze_script: str,
    edited_script: str,
    output_dir: str,
    timestamp: datetime | None = None,
) -> dict:
    """
    记录 GroundTruth 到本地目录
    
    Args:
        task_id: 任务 ID
        company: 公司名称
        reference_text: 标准文案
        original_video_url: 原视频 URL
        original_video_tos_key: 原视频 TOS key
        asr_result: ASR 结果（字典或路径）
        analyze_script: 系统输出的 script
        edited_script: 用户编辑后的 script
        output_dir: 输出目录
        timestamp: 时间戳，默认为当前时间
    
    Returns:
        产物信息字典
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 保存 reference.txt
    reference_path = output_path / "reference.txt"
    reference_path.write_text(reference_text, encoding="utf-8")
    
    # 保存 analyze_script.txt
    analyze_script_path = output_path / "analyze_script.txt"
    analyze_script_path.write_text(analyze_script, encoding="utf-8")
    
    # 保存 edited_script.txt
    edited_script_path = output_path / "edited_script.txt"
    edited_script_path.write_text(edited_script, encoding="utf-8")
    
    # 保存 asr_result.json
    asr_result_path = output_path / "asr_result.json"
    if isinstance(asr_result, dict):
        asr_data = asr_result
    else:
        # 从文件加载
        asr_source = Path(asr_result)
        if asr_source.exists():
            asr_data = json.loads(asr_source.read_text(encoding="utf-8"))
        else:
            asr_data = {"error": "ASR result not found", "path": str(asr_result)}
    
    with open(asr_result_path, "w", encoding="utf-8") as f:
        json.dump(asr_data, f, ensure_ascii=False, indent=2)
    
    # 保存 metadata.json
    metadata = {
        "task_id": task_id,
        "company": company,
        "created_at": timestamp.isoformat(),
        "reference_text": reference_text,
        "original_video_url": original_video_url,
        "original_video_tos_key": original_video_tos_key,
        "asr_result_url": None,  # 将在上传后填充
        "analyze_script": analyze_script,
        "edited_script": edited_script,
    }
    
    metadata_path = output_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    logger.info(f"GroundTruth recorded to {output_dir}")
    
    return {
        "output_dir": output_dir,
        "reference_path": str(reference_path),
        "analyze_script_path": str(analyze_script_path),
        "edited_script_path": str(edited_script_path),
        "asr_result_path": str(asr_result_path),
        "metadata_path": str(metadata_path),
        "metadata": metadata,
    }


def build_groundtruth_tos_path(
    company: str,
    timestamp: datetime | None = None,
) -> str:
    """
    构建 GroundTruth 在 TOS 上的存储路径
    
    路径格式：cujian_input_data/{company}/{year-month}/cujian_userdata_{timestamp}/
    
    Args:
        company: 公司名称
        timestamp: 时间戳，默认为当前时间
    
    Returns:
        TOS 路径前缀
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    year_month = timestamp.strftime("%Y-%m")
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    return f"{TOS_CUJIAN_INPUT_DATA_PREFIX}/{company}/{year_month}/cujian_userdata_{timestamp_str}"


def upload_groundtruth(
    local_dir: str,
    tos_prefix: str,
    upload_fn: callable,
) -> dict:
    """
    上传 GroundTruth 到 TOS
    
    Args:
        local_dir: 本地目录路径
        tos_prefix: TOS 路径前缀
        upload_fn: 上传函数，接收 (local_path, object_key) 返回 url
    
    Returns:
        上传结果字典
    """
    local_path = Path(local_dir)
    
    files_to_upload = [
        ("reference.txt", "reference.txt"),
        ("analyze_script.txt", "analyze_script.txt"),
        ("edited_script.txt", "edited_script.txt"),
        ("asr_result.json", "asr_result.json"),
        ("metadata.json", "metadata.json"),
    ]
    
    uploaded_files = {}
    
    for local_name, object_suffix in files_to_upload:
        local_file = local_path / local_name
        if local_file.exists():
            object_key = f"{tos_prefix}/{object_suffix}"
            url = upload_fn(str(local_file), object_key)
            uploaded_files[local_name] = {
                "url": url,
                "key": object_key,
            }
            logger.debug(f"Uploaded {local_name} to {object_key}")
    
    # 更新 metadata.json 中的 URL
    if "metadata.json" in uploaded_files:
        metadata_key = uploaded_files["metadata.json"]["key"]
        metadata_url = uploaded_files["metadata.json"]["url"]
        
        # 构建 asr_result URL
        asr_key = f"{tos_prefix}/asr_result.json"
        # 假设可以通过 key 推导 URL，或者在实际实现中从 upload_fn 返回
        
        logger.info(f"GroundTruth uploaded to {tos_prefix}")
    
    return {
        "tos_prefix": tos_prefix,
        "uploaded_files": uploaded_files,
    }


def create_groundtruth_pipeline(
    task_id: str,
    company: str,
    reference_text: str,
    original_video_url: str,
    original_video_tos_key: str,
    asr_result_url: str,
    analyze_script: str,
    edited_script: str,
    work_dir: str,
    upload_fn: callable,
    download_fn: callable,
    timestamp: datetime | None = None,
) -> dict:
    """
    GroundTruth 完整流程
    
    Args:
        task_id: 任务 ID
        company: 公司名称
        reference_text: 标准文案
        original_video_url: 原视频 URL
        original_video_tos_key: 原视频 TOS key
        asr_result_url: ASR 结果 URL
        analyze_script: 系统输出的 script
        edited_script: 用户编辑后的 script
        work_dir: 工作目录
        upload_fn: 上传函数，接收 (local_path, object_key) 返回 url
        download_fn: 下载函数，接收 (url, local_path) 返回 local_path
        timestamp: 时间戳
    
    Returns:
        处理结果字典，包含:
        - success: 是否成功
        - local_dir: 本地目录路径
        - tos_prefix: TOS 路径前缀
        - groundtruth_url: GroundTruth 目录的 URL（与模型定义一致）
        - groundtruth_tos_key: GroundTruth 目录的 TOS key（与模型定义一致）
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # 构建本地输出目录
    local_dir = Path(work_dir) / "groundtruth"
    local_dir.mkdir(parents=True, exist_ok=True)
    
    # 下载 ASR 结果
    asr_result_path = local_dir / "asr_result_downloaded.json"
    try:
        download_fn(asr_result_url, str(asr_result_path))
        with open(asr_result_path, "r", encoding="utf-8") as f:
            asr_result = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to download ASR result, using empty dict: {e}")
        asr_result = {}
    
    # 记录 GroundTruth
    record_result = record_groundtruth(
        task_id=task_id,
        company=company,
        reference_text=reference_text,
        original_video_url=original_video_url,
        original_video_tos_key=original_video_tos_key,
        asr_result=asr_result,
        analyze_script=analyze_script,
        edited_script=edited_script,
        output_dir=str(local_dir),
        timestamp=timestamp,
    )
    
    # 更新 metadata 中的 asr_result_url
    metadata_path = local_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        metadata["asr_result_url"] = asr_result_url
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 构建 TOS 路径
    tos_prefix = build_groundtruth_tos_path(company, timestamp)
    
    # 上传
    try:
        upload_result = upload_groundtruth(
            local_dir=str(local_dir),
            tos_prefix=tos_prefix,
            upload_fn=upload_fn,
        )
        
        # 返回目录级 GroundTruth 标识，而不是某个单文件 URL。
        # 这里的 groundtruth_url / groundtruth_tos_key 都使用目录前缀语义，
        # 上层如果需要访问具体文件，应再拼接具体文件名。
        return {
            "success": True,
            "local_dir": str(local_dir),
            "tos_prefix": tos_prefix,
            "groundtruth_url": tos_prefix,
            "groundtruth_tos_key": tos_prefix,
        }
    except Exception as e:
        logger.error(f"GroundTruth upload failed: {e}")
        # 上传失败不阻塞最终视频成功，但记录失败状态
        return {
            "success": False,
            "local_dir": str(local_dir),
            "tos_prefix": tos_prefix,
            "error": str(e),
        }
