"""
在线版最终视频切割模块

基于 DirectCutter 的切割逻辑，但支持动态码率参数。
解决原 DirectCutter 固定输出参数无法满足 min(input_bitrate, 12Mbps) 要求的问题。

规格来源：doc/cujian_plan_cx2.md 5.3 节
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OnlineFinalVideoCutter:
    """
    在线版最终视频切割器
    
    职责：
    1. 复用 DirectCutter 的 cuts 计算逻辑
    2. 自己生成 filter_complex
    3. 自己执行 ffmpeg，支持动态码率参数
    """
    
    def __init__(self, video_path: str):
        """
        初始化切割器
        
        Args:
            video_path: 输入视频文件路径
        """
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        self.delay_cuts: list[dict] = []
        self.pause_cuts: list[dict] = []
        self.keep_segments: list[dict] = []
        
        # 获取视频信息
        self.video_info = self._probe_video_info(video_path)
    
    def load_delay_cuts(self, path: str) -> "OnlineFinalVideoCutter":
        """
        加载延迟切割点
        
        Args:
            path: delay cuts JSON 文件路径
        
        Returns:
            self，支持链式调用
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 支持两种格式：列表或 cut_segments 包装
        if isinstance(data, list):
            self.delay_cuts = data
        elif isinstance(data, dict):
            self.delay_cuts = data.get("cut_segments", [])
            # 如果是毫秒格式，转换为秒
            if self.delay_cuts and "start_time" in self.delay_cuts[0]:
                if self.delay_cuts[0]["start_time"] > 1000:  # 推测为毫秒
                    self.delay_cuts = [
                        {
                            "start_time": c["start_time"] / 1000.0,
                            "end_time": c["end_time"] / 1000.0,
                            "type": c.get("type", "discard"),
                        }
                        for c in self.delay_cuts
                    ]
        
        logger.info(f"Loaded {len(self.delay_cuts)} delay cuts from {path}")
        return self
    
    def load_pause_cuts(self, path: str) -> "OnlineFinalVideoCutter":
        """
        加载暂停切割点
        
        Args:
            path: pause cuts JSON 文件路径（DirectCutter 兼容格式）
        
        Returns:
            self，支持链式调用
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cuts = data.get("cut_segments", [])
        
        # 转换为秒级时间
        self.pause_cuts = [
            {
                "start_time": c["start_time"] / 1000.0,  # 毫秒转秒
                "end_time": c["end_time"] / 1000.0,
                "type": c.get("type", "pause"),
            }
            for c in cuts
        ]
        
        logger.info(f"Loaded {len(self.pause_cuts)} pause cuts from {path}")
        return self
    
    def calculate_keep_segments(self) -> list[dict]:
        """
        计算需要保留的片段
        
        合并 delay_cuts 和 pause_cuts，然后计算保留片段。
        
        Returns:
            保留片段列表，每个元素包含 start, end（秒）
        """
        # 合并所有切割点
        all_cuts = self.delay_cuts + self.pause_cuts
        
        if not all_cuts:
            # 没有切割点，保留整个视频
            duration = self.video_info.get("duration", 0)
            self.keep_segments = [{"start": 0.0, "end": duration}]
            return self.keep_segments
        
        # 提取所有切割区间
        discard_segments = []
        for cut in all_cuts:
            start = float(cut.get("start_time", 0))
            end = float(cut.get("end_time", 0))
            
            if start < end:
                discard_segments.append({"start": start, "end": end})
        
        # 按开始时间排序
        discard_segments.sort(key=lambda x: x["start"])
        
        # 合并重叠的切割区间
        merged_discards = []
        for segment in discard_segments:
            if not merged_discards:
                merged_discards.append(segment)
            else:
                last = merged_discards[-1]
                if segment["start"] <= last["end"]:
                    # 重叠或相邻，合并
                    last["end"] = max(last["end"], segment["end"])
                else:
                    merged_discards.append(segment)
        
        # 计算保留片段（丢弃片段之间的部分）
        duration = self.video_info.get("duration", 0)
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
        if current_pos < duration:
            keep_segments.append({
                "start": current_pos,
                "end": duration,
            })
        
        self.keep_segments = keep_segments
        logger.info(
            f"Calculated {len(keep_segments)} keep segments, "
            f"total duration: {sum(s['end'] - s['start'] for s in keep_segments):.3f}s"
        )
        return keep_segments
    
    def save_cut_plan(self, path: str) -> str:
        """
        保存切割计划到文件
        
        Args:
            path: 输出文件路径
        
        Returns:
            输出文件路径
        """
        plan = {
            "video_path": str(self.video_path),
            "video_info": self.video_info,
            "delay_cuts": self.delay_cuts,
            "pause_cuts": self.pause_cuts,
            "keep_segments": self.keep_segments,
        }
        
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Cut plan saved to {path}")
        return path
    
    def cut(
        self,
        output_path: str,
        *,
        video_bitrate: int,
        maxrate: int | None = None,
        bufsize: int | None = None,
        preset: str = "veryfast",
        audio_bitrate: str = "192k",
    ) -> str:
        """
        执行视频切割
        
        Args:
            output_path: 输出视频路径
            video_bitrate: 视频码率（bps）
            maxrate: 最大码率（bps），默认为 video_bitrate
            bufsize: 缓冲区大小（bps），默认为 video_bitrate * 2
            preset: x264 预设
            audio_bitrate: 音频码率
        
        Returns:
            输出文件路径
        
        Raises:
            RuntimeError: 当 FFmpeg 执行失败时
        """
        if not self.keep_segments:
            self.calculate_keep_segments()
        
        if not self.keep_segments:
            raise ValueError("没有需要保留的片段")
        
        # 设置默认参数
        maxrate = maxrate or video_bitrate
        bufsize = bufsize or video_bitrate * 2
        
        # 确保输出目录存在
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建 FFmpeg 命令
        if len(self.keep_segments) == 1:
            # 单段，直接裁剪
            seg = self.keep_segments[0]
            cmd = self._build_single_segment_cmd(
                seg["start"], seg["end"], output_path,
                video_bitrate, maxrate, bufsize, preset, audio_bitrate
            )
        else:
            # 多段，使用 filter_complex
            cmd = self._build_multi_segment_cmd(
                output_path,
                video_bitrate, maxrate, bufsize, preset, audio_bitrate
            )
        
        logger.info(f"Executing FFmpeg: {' '.join(cmd)}")
        
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
        
        logger.info(f"Video cut completed: {output_path}")
        return output_path
    
    def _build_single_segment_cmd(
        self,
        start: float,
        end: float,
        output_path: str,
        video_bitrate: int,
        maxrate: int,
        bufsize: int,
        preset: str,
        audio_bitrate: str,
    ) -> list[str]:
        """构建单段裁剪的 FFmpeg 命令"""
        duration = end - start
        
        return [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "warning",
            "-ss", str(start),
            "-t", str(duration),
            "-i", str(self.video_path),
            "-c:v", "libx264",
            "-preset", preset,
            "-b:v", str(video_bitrate),
            "-maxrate", str(maxrate),
            "-bufsize", str(bufsize),
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-avoid_negative_ts", "make_zero",
            "-fflags", "+genpts",
            output_path,
        ]
    
    def _build_multi_segment_cmd(
        self,
        output_path: str,
        video_bitrate: int,
        maxrate: int,
        bufsize: int,
        preset: str,
        audio_bitrate: str,
    ) -> list[str]:
        """构建多段拼接的 FFmpeg 命令"""
        # 构建 filter_complex
        video_filters = []
        audio_filters = []
        video_labels = []
        audio_labels = []
        
        for i, seg in enumerate(self.keep_segments):
            v_label = f"[v{i}]"
            a_label = f"[a{i}]"
            video_labels.append(v_label)
            audio_labels.append(a_label)
            
            # 视频裁剪
            video_filters.append(
                f"[0:v]trim=start={seg['start']}:end={seg['end']},setpts=PTS-STARTPTS{v_label}"
            )
            # 音频裁剪
            audio_filters.append(
                f"[0:a]atrim=start={seg['start']}:end={seg['end']},asetpts=PTS-STARTPTS{a_label}"
            )
        
        # concat 过滤器
        v_concat = "".join(video_labels)
        a_concat = "".join(audio_labels)
        num_segments = len(self.keep_segments)
        
        video_filters.append(
            f"{v_concat}concat=n={num_segments}:v=1:a=0[outv]"
        )
        audio_filters.append(
            f"{a_concat}concat=n={num_segments}:v=0:a=1[outa]"
        )
        
        filter_complex = ";".join(video_filters + audio_filters)
        
        return [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "warning",
            "-i", str(self.video_path),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", preset,
            "-b:v", str(video_bitrate),
            "-maxrate", str(maxrate),
            "-bufsize", str(bufsize),
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            output_path,
        ]
    
    def _probe_video_info(self, video_path: str) -> dict[str, Any]:
        """
        探测视频信息
        
        Args:
            video_path: 视频文件路径
        
        Returns:
            视频信息字典
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,bit_rate",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "json",
            video_path,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
            
            # 提取信息
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            video_stream = None
            for s in streams:
                if s.get("codec_type") == "video":
                    video_stream = s
                    break
            
            info = {
                "duration": float(format_info.get("duration", 0)),
                "bit_rate": int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None,
                "width": video_stream.get("width") if video_stream else None,
                "height": video_stream.get("height") if video_stream else None,
                "frame_rate": video_stream.get("r_frame_rate") if video_stream else None,
            }
            
            return info
        except Exception as e:
            logger.warning(f"Failed to probe video info: {e}")
            return {"duration": 0}


def calculate_output_bitrate(input_bitrate: int | None, max_bitrate: int = 12_000_000) -> int:
    """
    计算输出码率
    
    规则：min(input_bitrate, max_bitrate)
    如果无法获取输入码率，则使用 max_bitrate
    
    Args:
        input_bitrate: 输入视频码率（bps），可能为 None
        max_bitrate: 最大允许码率（bps），默认 12Mbps
    
    Returns:
        输出码率（bps）
    """
    if input_bitrate is None or input_bitrate <= 0:
        return max_bitrate
    return min(input_bitrate, max_bitrate)


def cut_final_video(
    video_path: str,
    delay_cuts_path: str,
    pause_cuts_path: str,
    output_path: str,
    input_bitrate: int | None = None,
    max_bitrate: int = 12_000_000,
    cut_plan_path: str | None = None,
) -> dict:
    """
    便捷函数：执行最终视频切割
    
    Args:
        video_path: 输入视频路径
        delay_cuts_path: delay cuts JSON 路径
        pause_cuts_path: pause cuts JSON 路径（DirectCutter 格式）
        output_path: 输出视频路径
        input_bitrate: 输入视频码率，如果为 None 则自动探测
        max_bitrate: 最大输出码率
        cut_plan_path: 可选，保存切割计划的路径
    
    Returns:
        包含结果信息的字典
    """
    cutter = OnlineFinalVideoCutter(video_path)
    
    # 加载切割点
    cutter.load_delay_cuts(delay_cuts_path)
    cutter.load_pause_cuts(pause_cuts_path)
    
    # 计算保留片段
    cutter.calculate_keep_segments()
    
    # 保存切割计划
    if cut_plan_path:
        cutter.save_cut_plan(cut_plan_path)
    
    # 计算输出码率
    actual_input_bitrate = input_bitrate or cutter.video_info.get("bit_rate")
    output_bitrate = calculate_output_bitrate(actual_input_bitrate, max_bitrate)
    
    # 执行切割
    cutter.cut(
        output_path,
        video_bitrate=output_bitrate,
        maxrate=output_bitrate,
        bufsize=output_bitrate * 2,
    )
    
    return {
        "output_path": output_path,
        "input_bitrate": actual_input_bitrate,
        "output_bitrate": output_bitrate,
        "keep_segments": cutter.keep_segments,
        "cut_plan_path": cut_plan_path,
    }
