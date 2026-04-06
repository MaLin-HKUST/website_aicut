"""
Finalize Processor 的单元测试
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.finalize_processor import (
    process_finalize,
    _get_video_bitrate,
    OutputMode,
)


class TestGetVideoBitrate:
    """测试 _get_video_bitrate 函数"""
    
    @patch('subprocess.run')
    def test_get_bitrate_success(self, mock_run):
        """测试成功获取码率"""
        mock_run.return_value = Mock(
            stdout="8000000\n",
            stderr="",
            returncode=0,
        )
        
        result = _get_video_bitrate("/path/to/video.mp4")
        assert result == 8000000
    
    @patch('subprocess.run')
    def test_get_bitrate_empty_output(self, mock_run):
        """测试空输出返回 None"""
        mock_run.return_value = Mock(
            stdout="\n",
            stderr="",
            returncode=0,
        )
        
        result = _get_video_bitrate("/path/to/video.mp4")
        assert result is None
    
    @patch('subprocess.run')
    def test_get_bitrate_error(self, mock_run):
        """测试错误返回 None"""
        mock_run.side_effect = Exception("ffprobe error")
        
        result = _get_video_bitrate("/path/to/video.mp4")
        assert result is None


class TestProcessFinalizeOriginalMode:
    """测试 process_finalize - Original 模式"""
    
    @patch('src.finalize_processor.OnlineFinalVideoCutter')
    @patch('src.finalize_processor._get_video_bitrate')
    def test_original_mode(self, mock_get_bitrate, mock_cutter_class):
        """测试 original 模式"""
        mock_get_bitrate.return_value = 8000000
        
        mock_cutter = Mock()
        mock_cutter.video_info = {"duration": 120}
        mock_cutter_class.return_value = mock_cutter
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir, "video.mp4")
            video_path.touch()
            delay_cuts_path = Path(tmpdir, "delay_cuts.json")
            delay_cuts_path.write_text("[]")
            pause_cuts_path = Path(tmpdir, "pause_cuts.json")
            pause_cuts_path.write_text('{"cut_segments": []}')
            
            result = process_finalize(
                task_id="123",
                original_video_path=str(video_path),
                edited_delay_cuts_path=str(delay_cuts_path),
                pause_cuts_on_original_path=str(pause_cuts_path),
                output_mode=OutputMode.ORIGINAL,
                output_dir=tmpdir,
            )
            
            assert result["task_id"] == "123"
            assert result["output_mode"] == OutputMode.ORIGINAL
            assert "final_video_path" in result
            assert "encoding_params" in result
            assert result["encoding_params"]["mode"] == OutputMode.ORIGINAL
            
            # 验证没有 normalized 产物
            assert "normalized_video_path" not in result
            assert "normalized_process_path" not in result


class TestProcessFinalizeVerticalMode:
    """测试 process_finalize - Vertical 1080P 模式"""
    
    @patch('src.finalize_processor._normalize_video')
    @patch('src.finalize_processor.OnlineFinalVideoCutter')
    @patch('src.finalize_processor._get_video_bitrate')
    def test_vertical_1080p_mode(self, mock_get_bitrate, mock_cutter_class, mock_normalize):
        """测试 vertical_1080p 模式"""
        mock_get_bitrate.return_value = 8000000
        
        # Mock normalize 返回归一化视频路径
        mock_normalize.return_value = (
            "/path/to/normalized.mp4",
            "/path/to/normalized.process.json",
        )
        
        mock_cutter = Mock()
        mock_cutter.video_info = {"duration": 120}
        mock_cutter_class.return_value = mock_cutter
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir, "video.mp4")
            video_path.touch()
            delay_cuts_path = Path(tmpdir, "delay_cuts.json")
            delay_cuts_path.write_text("[]")
            pause_cuts_path = Path(tmpdir, "pause_cuts.json")
            pause_cuts_path.write_text('{"cut_segments": []}')
            
            result = process_finalize(
                task_id="123",
                original_video_path=str(video_path),
                edited_delay_cuts_path=str(delay_cuts_path),
                pause_cuts_on_original_path=str(pause_cuts_path),
                output_mode=OutputMode.VERTICAL_1080P,
                output_dir=tmpdir,
            )
            
            assert result["output_mode"] == OutputMode.VERTICAL_1080P
            
            # 验证 normalize 被调用
            mock_normalize.assert_called_once()
            
            # 验证有 normalized 产物
            assert "normalized_video_path" in result
            assert "normalized_process_path" in result


class TestProcessFinalizeValidation:
    """测试 process_finalize 参数验证"""
    
    def test_invalid_output_mode(self):
        """测试无效的输出模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                process_finalize(
                    task_id="123",
                    original_video_path=str(Path(tmpdir, "video.mp4")),
                    edited_delay_cuts_path=str(Path(tmpdir, "delay.json")),
                    pause_cuts_on_original_path=str(Path(tmpdir, "pause.json")),
                    output_mode="invalid_mode",
                )
            assert "无效的输出模式" in str(exc_info.value)


class TestEncodingParams:
    """测试编码参数"""
    
    @patch('src.finalize_processor.OnlineFinalVideoCutter')
    @patch('src.finalize_processor._get_video_bitrate')
    def test_output_bitrate_calculation(self, mock_get_bitrate, mock_cutter_class):
        """测试输出码率计算"""
        # 输入码率 8Mbps，应该输出 8Mbps（小于 12Mbps）
        mock_get_bitrate.return_value = 8_000_000
        
        mock_cutter = Mock()
        mock_cutter.video_info = {"duration": 120}
        mock_cutter_class.return_value = mock_cutter
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir, "video.mp4")
            video_path.touch()
            delay_cuts_path = Path(tmpdir, "delay_cuts.json")
            delay_cuts_path.write_text("[]")
            pause_cuts_path = Path(tmpdir, "pause_cuts.json")
            pause_cuts_path.write_text('{"cut_segments": []}')
            
            result = process_finalize(
                task_id="123",
                original_video_path=str(video_path),
                edited_delay_cuts_path=str(delay_cuts_path),
                pause_cuts_on_original_path=str(pause_cuts_path),
                output_mode=OutputMode.ORIGINAL,
                output_dir=tmpdir,
            )
            
            encoding = result["encoding_params"]
            assert encoding["input_bitrate"] == 8_000_000
            assert encoding["output_bitrate"] == 8_000_000  # min(8M, 12M) = 8M
            assert encoding["maxrate"] == 8_000_000
            assert encoding["bufsize"] == 16_000_000  # 2 * output_bitrate
    
    @patch('src.finalize_processor.OnlineFinalVideoCutter')
    @patch('src.finalize_processor._get_video_bitrate')
    def test_output_bitrate_capped_at_12mbps(self, mock_get_bitrate, mock_cutter_class):
        """测试输出码率被限制在 12Mbps"""
        # 输入码率 15Mbps，应该输出 12Mbps
        mock_get_bitrate.return_value = 15_000_000
        
        mock_cutter = Mock()
        mock_cutter.video_info = {"duration": 120}
        mock_cutter_class.return_value = mock_cutter
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir, "video.mp4")
            video_path.touch()
            delay_cuts_path = Path(tmpdir, "delay_cuts.json")
            delay_cuts_path.write_text("[]")
            pause_cuts_path = Path(tmpdir, "pause_cuts.json")
            pause_cuts_path.write_text('{"cut_segments": []}')
            
            result = process_finalize(
                task_id="123",
                original_video_path=str(video_path),
                edited_delay_cuts_path=str(delay_cuts_path),
                pause_cuts_on_original_path=str(pause_cuts_path),
                output_mode=OutputMode.ORIGINAL,
                output_dir=tmpdir,
            )
            
            encoding = result["encoding_params"]
            assert encoding["input_bitrate"] == 15_000_000
            assert encoding["output_bitrate"] == 12_000_000  # min(15M, 12M) = 12M


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
