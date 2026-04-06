"""
最终视频切割模块的单元测试

注意：这些测试需要 FFmpeg 环境才能运行
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.final_video_cutter import (
    OnlineFinalVideoCutter,
    calculate_output_bitrate,
    cut_final_video,
)


class TestCalculateOutputBitrate:
    """测试 calculate_output_bitrate 函数"""
    
    def test_input_less_than_max(self):
        """测试输入码率小于最大码率"""
        result = calculate_output_bitrate(8_000_000, 12_000_000)
        assert result == 8_000_000
    
    def test_input_greater_than_max(self):
        """测试输入码率大于最大码率"""
        result = calculate_output_bitrate(15_000_000, 12_000_000)
        assert result == 12_000_000
    
    def test_input_equal_to_max(self):
        """测试输入码率等于最大码率"""
        result = calculate_output_bitrate(12_000_000, 12_000_000)
        assert result == 12_000_000
    
    def test_input_none(self):
        """测试输入码率为 None"""
        result = calculate_output_bitrate(None, 12_000_000)
        assert result == 12_000_000
    
    def test_input_zero(self):
        """测试输入码率为 0"""
        result = calculate_output_bitrate(0, 12_000_000)
        assert result == 12_000_000
    
    def test_input_negative(self):
        """测试输入码率为负数"""
        result = calculate_output_bitrate(-1, 12_000_000)
        assert result == 12_000_000


class TestOnlineFinalVideoCutterInit:
    """测试 OnlineFinalVideoCutter 初始化"""
    
    def test_init_with_nonexistent_file(self):
        """测试初始化不存在的文件"""
        with pytest.raises(FileNotFoundError):
            OnlineFinalVideoCutter("/nonexistent/video.mp4")
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_init_with_existing_file(self, mock_run):
        """测试初始化存在的文件"""
        mock_run.return_value = Mock(
            stdout=json.dumps({
                "format": {"duration": "120.5", "bit_rate": "8000000"},
                "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]
            }),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            assert cutter.video_path == Path(path)
            assert cutter.video_info["duration"] == 120.5
        finally:
            Path(path).unlink()


class TestLoadCuts:
    """测试加载切割点"""
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_load_delay_cuts_list_format(self, mock_run):
        """测试加载列表格式的 delay cuts"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.touch()
            
            delay_cuts_path = Path(tmpdir) / "delay_cuts.json"
            with open(delay_cuts_path, 'w') as f:
                json.dump([
                    {"start_time": 10.0, "end_time": 15.0},
                ], f)
            
            cutter = OnlineFinalVideoCutter(str(video_path))
            cutter.load_delay_cuts(str(delay_cuts_path))
            
            assert len(cutter.delay_cuts) == 1
            assert cutter.delay_cuts[0]["start_time"] == 10.0
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_load_delay_cuts_milliseconds(self, mock_run):
        """测试加载毫秒格式的 delay cuts"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.touch()
            
            delay_cuts_path = Path(tmpdir) / "delay_cuts.json"
            with open(delay_cuts_path, 'w') as f:
                json.dump({
                    "cut_segments": [
                        {"start_time": 10000, "end_time": 15000},  # 毫秒
                    ]
                }, f)
            
            cutter = OnlineFinalVideoCutter(str(video_path))
            cutter.load_delay_cuts(str(delay_cuts_path))
            
            assert len(cutter.delay_cuts) == 1
            assert cutter.delay_cuts[0]["start_time"] == 10.0  # 转换为秒
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_load_pause_cuts(self, mock_run):
        """测试加载 pause cuts"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.touch()
            
            pause_cuts_path = Path(tmpdir) / "pause_cuts.json"
            with open(pause_cuts_path, 'w') as f:
                json.dump({
                    "cut_segments": [
                        {"start_time": 5000, "end_time": 6500, "type": "pause"},
                    ]
                }, f)
            
            cutter = OnlineFinalVideoCutter(str(video_path))
            cutter.load_pause_cuts(str(pause_cuts_path))
            
            assert len(cutter.pause_cuts) == 1
            assert cutter.pause_cuts[0]["start_time"] == 5.0  # 转换为秒


class TestCalculateKeepSegments:
    """测试计算保留片段"""
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_no_cuts(self, mock_run):
        """测试没有切割点的情况"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            cutter.calculate_keep_segments()
            
            assert len(cutter.keep_segments) == 1
            assert cutter.keep_segments[0]["start"] == 0.0
            assert cutter.keep_segments[0]["end"] == 120.0
        finally:
            Path(path).unlink()
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_single_delay_cut(self, mock_run):
        """测试单个 delay cut"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            cutter.delay_cuts = [
                {"start_time": 10.0, "end_time": 20.0},
            ]
            cutter.calculate_keep_segments()
            
            # 应该产生两个保留片段：[0-10] 和 [20-120]
            assert len(cutter.keep_segments) == 2
            assert cutter.keep_segments[0] == {"start": 0.0, "end": 10.0}
            assert cutter.keep_segments[1] == {"start": 20.0, "end": 120.0}
        finally:
            Path(path).unlink()
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_delay_and_pause_cuts(self, mock_run):
        """测试同时有 delay cuts 和 pause cuts"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            cutter.delay_cuts = [
                {"start_time": 10.0, "end_time": 20.0},
            ]
            cutter.pause_cuts = [
                {"start_time": 50.0, "end_time": 55.0},
            ]
            cutter.calculate_keep_segments()
            
            # 应该产生三个保留片段：[0-10], [20-50], [55-120]
            assert len(cutter.keep_segments) == 3
        finally:
            Path(path).unlink()
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_overlapping_cuts(self, mock_run):
        """测试重叠的切割点"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            cutter.delay_cuts = [
                {"start_time": 10.0, "end_time": 20.0},
            ]
            cutter.pause_cuts = [
                {"start_time": 15.0, "end_time": 25.0},  # 与 delay 重叠
            ]
            cutter.calculate_keep_segments()
            
            # 应该产生两个保留片段：[0-10] 和 [25-120]
            assert len(cutter.keep_segments) == 2
            assert cutter.keep_segments[0] == {"start": 0.0, "end": 10.0}
            assert cutter.keep_segments[1] == {"start": 25.0, "end": 120.0}
        finally:
            Path(path).unlink()


class TestSaveCutPlan:
    """测试保存切割计划"""
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_save_cut_plan(self, mock_run):
        """测试保存切割计划"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.touch()
            
            cutter = OnlineFinalVideoCutter(str(video_path))
            cutter.delay_cuts = [{"start_time": 10.0, "end_time": 20.0}]
            cutter.pause_cuts = [{"start_time": 50.0, "end_time": 55.0}]
            cutter.keep_segments = [{"start": 0.0, "end": 10.0}]
            
            plan_path = Path(tmpdir) / "cut_plan.json"
            cutter.save_cut_plan(str(plan_path))
            
            assert plan_path.exists()
            
            with open(plan_path, 'r') as f:
                plan = json.load(f)
            
            assert plan["video_path"] == str(video_path)
            assert len(plan["delay_cuts"]) == 1
            assert len(plan["pause_cuts"]) == 1
            assert len(plan["keep_segments"]) == 1


class TestBuildFilterComplex:
    """测试构建 filter_complex"""
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_build_single_segment_cmd(self, mock_run):
        """测试单段裁剪命令"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            cmd = cutter._build_single_segment_cmd(
                start=10.0,
                end=20.0,
                output_path="/output.mp4",
                video_bitrate=8_000_000,
                maxrate=8_000_000,
                bufsize=16_000_000,
                preset="veryfast",
                audio_bitrate="192k",
            )
            
            assert "ffmpeg" in cmd
            assert "-ss" in cmd
            assert "10.0" in cmd
            assert "-t" in cmd
            assert "10.0" in cmd  # duration = 20 - 10
            assert "-b:v" in cmd
            assert "8000000" in cmd
        finally:
            Path(path).unlink()
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_build_multi_segment_cmd(self, mock_run):
        """测试多段拼接命令"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            path = f.name
        
        try:
            cutter = OnlineFinalVideoCutter(path)
            cutter.keep_segments = [
                {"start": 0.0, "end": 10.0},
                {"start": 20.0, "end": 30.0},
            ]
            
            cmd = cutter._build_multi_segment_cmd(
                output_path="/output.mp4",
                video_bitrate=8_000_000,
                maxrate=8_000_000,
                bufsize=16_000_000,
                preset="veryfast",
                audio_bitrate="192k",
            )
            
            assert "ffmpeg" in cmd
            assert "-filter_complex" in cmd
            assert "concat" in cmd
            assert "n=2" in cmd  # 2 segments
        finally:
            Path(path).unlink()


class TestCutFinalVideo:
    """测试 cut_final_video 便捷函数"""
    
    @patch('src.final_video_cutter.subprocess.run')
    def test_cut_final_video(self, mock_run):
        """测试完整流程"""
        mock_run.return_value = Mock(
            stdout=json.dumps({"format": {"duration": "120", "bit_rate": "8000000"}}),
            stderr="",
            returncode=0,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            video_path.touch()
            
            delay_cuts_path = Path(tmpdir) / "delay_cuts.json"
            with open(delay_cuts_path, 'w') as f:
                json.dump([], f)
            
            pause_cuts_path = Path(tmpdir) / "pause_cuts.json"
            with open(pause_cuts_path, 'w') as f:
                json.dump({"cut_segments": []}, f)
            
            output_path = Path(tmpdir) / "output.mp4"
            
            result = cut_final_video(
                video_path=str(video_path),
                delay_cuts_path=str(delay_cuts_path),
                pause_cuts_path=str(pause_cuts_path),
                output_path=str(output_path),
            )
            
            assert "output_path" in result
            assert "input_bitrate" in result
            assert "output_bitrate" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
