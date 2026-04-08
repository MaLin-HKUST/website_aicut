"""Video Info Utils - 视频信息获取工具

提供视频信息获取功能：
1. 获取视频基本信息（分辨率、时长、码率等）
2. 视频格式检测
3. 视频帧率获取
4. 获取视频码率和分辨率（简化接口）
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """视频信息数据类"""
    path: Path
    width: int
    height: int
    duration: float
    bitrate: int
    fps: float
    codec: str
    file_size: int
    
    @property
    def resolution(self) -> str:
        """分辨率字符串"""
        return f"{self.width}x{self.height}"
    
    @property
    def aspect_ratio(self) -> float:
        """宽高比"""
        return self.width / self.height if self.height > 0 else 0
    
    @property
    def is_portrait(self) -> bool:
        """是否为竖屏视频"""
        return self.height > self.width
    
    @property
    def is_landscape(self) -> bool:
        """是否为横屏视频"""
        return self.width > self.height
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "aspect_ratio": round(self.aspect_ratio, 2),
            "is_portrait": self.is_portrait,
            "is_landscape": self.is_landscape,
            "duration": self.duration,
            "bitrate": self.bitrate,
            "fps": self.fps,
            "codec": self.codec,
            "file_size": self.file_size,
        }


def get_video_info(video_path: Path, timeout: int = 30) -> Optional[VideoInfo]:
    """获取视频信息
    
    使用 ffprobe 获取视频详细信息。
    
    Args:
        video_path: 视频文件路径
        timeout: 命令超时时间（秒）
        
    Returns:
        VideoInfo: 视频信息对象，失败返回 None
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            logger.error(f"ffprobe failed: {result.stderr}")
            return None
        
        # 解析 JSON 输出
        probe_data = json.loads(result.stdout)
        
        # 获取视频流信息
        video_stream = None
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break
        
        if not video_stream:
            logger.error(f"No video stream found in {video_path}")
            return None
        
        # 获取格式信息
        format_info = probe_data.get("format", {})
        
        # 提取信息
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        
        # 时长
        duration_str = format_info.get("duration") or video_stream.get("duration")
        duration = float(duration_str) if duration_str else 0.0
        
        # 码率
        bitrate_str = format_info.get("bit_rate") or video_stream.get("bit_rate")
        bitrate = int(bitrate_str) if bitrate_str else 0
        
        # 帧率
        fps = _parse_fps(video_stream.get("r_frame_rate", "0/1"))
        
        # 编码格式
        codec = video_stream.get("codec_name", "unknown")
        
        # 文件大小
        size_str = format_info.get("size")
        file_size = int(size_str) if size_str else video_path.stat().st_size
        
        return VideoInfo(
            path=video_path,
            width=width,
            height=height,
            duration=duration,
            bitrate=bitrate,
            fps=fps,
            codec=codec,
            file_size=file_size
        )
        
    except FileNotFoundError:
        logger.error("ffprobe not found, cannot get video info")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timeout after {timeout}s")
        return None
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        return None


def _parse_fps(fps_str: str) -> float:
    """解析帧率字符串
    
    ffprobe 返回的帧率格式如 "30/1" 或 "30000/1001"
    
    Args:
        fps_str: 帧率字符串
        
    Returns:
        float: 帧率
    """
    try:
        if "/" in fps_str:
            num, den = map(int, fps_str.split("/"))
            return num / den if den != 0 else 0.0
        else:
            return float(fps_str)
    except Exception:
        return 0.0


def get_video_bitrate(video_path: Path, timeout: int = 30) -> int:
    """获取视频码率
    
    使用 ffprobe 获取视频码率，失败时返回估算值。
    
    Args:
        video_path: 视频文件路径
        timeout: 命令超时时间（秒）
        
    Returns:
        int: 码率 (bps)，失败时返回 0
    """
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
            if bitrate_str:
                try:
                    bitrate = int(bitrate_str)
                    if bitrate > 0:
                        return bitrate
                except ValueError:
                    pass
        
        # 尝试从 format 获取
        cmd_format = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd_format,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            bitrate_str = result.stdout.strip()
            if bitrate_str:
                try:
                    bitrate = int(bitrate_str)
                    if bitrate > 0:
                        return bitrate
                except ValueError:
                    pass
        
    except FileNotFoundError:
        logger.error("ffprobe not found, cannot get video bitrate")
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timeout after {timeout}s")
    except Exception as e:
        logger.error(f"Failed to get video bitrate: {e}")
    
    return 0


def get_video_resolution(video_path: Path, timeout: int = 30) -> Tuple[int, int]:
    """获取视频分辨率
    
    Args:
        video_path: 视频文件路径
        timeout: 命令超时时间（秒）
        
    Returns:
        Tuple[int, int]: (width, height)，失败返回 (0, 0)
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            resolution = result.stdout.strip()
            if "x" in resolution:
                width_str, height_str = resolution.split("x")
                return int(width_str), int(height_str)
        
    except FileNotFoundError:
        logger.error("ffprobe not found, cannot get video resolution")
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timeout after {timeout}s")
    except Exception as e:
        logger.error(f"Failed to get video resolution: {e}")
    
    return 0, 0


def get_video_duration(video_path: Path, timeout: int = 30) -> Optional[float]:
    """获取视频时长
    
    Args:
        video_path: 视频文件路径
        timeout: 命令超时时间（秒）
        
    Returns:
        float: 时长（秒），失败返回 None
    """
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


def is_valid_video(video_path: Path) -> bool:
    """检查是否为有效视频文件
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        bool: 是否为有效视频
    """
    if not video_path.exists():
        return False
    
    if not video_path.is_file():
        return False
    
    # 检查文件扩展名
    valid_extensions = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm"}
    if video_path.suffix.lower() not in valid_extensions:
        return False
    
    # 尝试获取视频信息
    info = get_video_info(video_path)
    return info is not None


def calculate_scaled_resolution(
    original_width: int,
    original_height: int,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None
) -> Tuple[int, int]:
    """计算缩放后的分辨率
    
    保持宽高比进行缩放。
    
    Args:
        original_width: 原始宽度
        original_height: 原始高度
        target_width: 目标宽度（可选）
        target_height: 目标高度（可选）
        
    Returns:
        Tuple[int, int]: 新的宽高
    """
    if target_width and target_height:
        # 同时指定了宽高
        return target_width, target_height
    
    aspect_ratio = original_width / original_height
    
    if target_width:
        # 根据宽度计算高度
        new_height = int(target_width / aspect_ratio)
        return target_width, new_height
    
    if target_height:
        # 根据高度计算宽度
        new_width = int(target_height * aspect_ratio)
        return new_width, target_height
    
    # 都没有指定，返回原尺寸
    return original_width, original_height
