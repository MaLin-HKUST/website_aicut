"""Bitrate Utils - 码率计算工具

提供视频码率计算功能：
1. 获取视频码率
2. 计算输出码率（上限控制）
3. 估算码率（ffprobe 失败时使用）
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)

# 默认码率限制 (12Mbps)
DEFAULT_MAX_BITRATE = 12_000_000

# 默认估算码率 (5Mbps)
DEFAULT_ESTIMATED_BITRATE = 5_000_000


def get_video_bitrate(video_path: Path, timeout: int = 30) -> int:
    """获取视频码率
    
    使用 ffprobe 获取视频码率。
    如果失败，通过文件大小估算。
    
    Args:
        video_path: 视频文件路径
        timeout: 命令超时时间（秒）
        
    Returns:
        int: 码率 (bps)
    """
    # 首先尝试使用 ffprobe
    bitrate = _get_bitrate_with_ffprobe(video_path, timeout)
    
    if bitrate and bitrate > 0:
        logger.debug(f"Got bitrate from ffprobe: {bitrate} bps")
        return bitrate
    
    # 失败时使用估算
    estimated = _estimate_bitrate_from_file_size(video_path)
    logger.warning(f"Using estimated bitrate: {estimated} bps")
    
    return estimated


def _get_bitrate_with_ffprobe(video_path: Path, timeout: int) -> Optional[int]:
    """使用 ffprobe 获取码率"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            bitrate_str = result.stdout.strip()
            if bitrate_str and bitrate_str.isdigit():
                bitrate = int(bitrate_str)
                if bitrate > 0:
                    return bitrate
        
        logger.warning(f"ffprobe returned invalid bitrate: {result.stdout}")
        
    except FileNotFoundError:
        logger.warning("ffprobe not found, cannot get video bitrate")
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timeout after {timeout}s")
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
    
    return None


def _estimate_bitrate_from_file_size(video_path: Path) -> int:
    """通过文件大小估算码率
    
    假设：
    - 视频时长：尝试获取，失败则假设 120 秒
    - 目标：保守估计，不高于默认估算值
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        int: 估算码率 (bps)
    """
    try:
        file_size = video_path.stat().st_size
        
        # 尝试获取视频时长
        duration = _get_video_duration(video_path)
        
        if duration and duration > 0:
            # 计算估算码率
            estimated = int(file_size * 8 / duration)
            # 限制在合理范围
            estimated = min(estimated, DEFAULT_ESTIMATED_BITRATE)
            estimated = max(estimated, 1_000_000)  # 最低 1Mbps
            return estimated
        else:
            # 无法获取时长，使用默认估算
            return DEFAULT_ESTIMATED_BITRATE
            
    except Exception as e:
        logger.warning(f"Failed to estimate bitrate: {e}")
        return DEFAULT_ESTIMATED_BITRATE


def _get_video_duration(video_path: Path, timeout: int = 30) -> Optional[float]:
    """获取视频时长"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            duration_str = result.stdout.strip()
            if duration_str:
                return float(duration_str)
        
    except Exception as e:
        logger.debug(f"Failed to get video duration: {e}")
    
    return None


def calculate_output_bitrate(
    input_bitrate: int,
    max_bitrate: int = DEFAULT_MAX_BITRATE,
    min_bitrate: int = 1_000_000
) -> int:
    """计算输出码率
    
    规则：
    - 输出码率 = min(输入码率, 最大码率)
    - 不低于最小码率
    
    Args:
        input_bitrate: 输入视频码率
        max_bitrate: 最大输出码率
        min_bitrate: 最小输出码率
        
    Returns:
        int: 输出码率 (bps)
    """
    output_bitrate = min(input_bitrate, max_bitrate)
    output_bitrate = max(output_bitrate, min_bitrate)
    
    logger.info(
        f"Bitrate calculation: input={input_bitrate}, "
        f"max={max_bitrate}, output={output_bitrate}"
    )
    
    return output_bitrate


def get_bitrate_for_resolution(resolution: str) -> int:
    """根据分辨率获取推荐码率
    
    Args:
        resolution: 分辨率字符串，如 "1920x1080", "1080x1920"
        
    Returns:
        int: 推荐码率 (bps)
    """
    # 解析分辨率
    try:
        width, height = map(int, resolution.lower().split('x'))
        pixels = width * height
        
        # 推荐码率表
        if pixels >= 3840 * 2160:  # 4K
            return 25_000_000
        elif pixels >= 1920 * 1080:  # 1080p
            return 8_000_000
        elif pixels >= 1280 * 720:  # 720p
            return 4_000_000
        elif pixels >= 854 * 480:  # 480p
            return 2_000_000
        else:
            return 1_000_000
            
    except Exception:
        return DEFAULT_ESTIMATED_BITRATE
