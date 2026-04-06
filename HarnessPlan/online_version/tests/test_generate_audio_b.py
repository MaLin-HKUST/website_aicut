"""
音频 B 生成模块的单元测试

注意：这些测试需要 FFmpeg 环境才能运行
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.generate_audio_b import (
    generate_audio_b,
    generate_audio_b_with_cuts,
    _calculate_keep_segments,
    _build_filter_complex,
    _get_audio_duration,
)


class TestCalculateKeepSegments:
    """测试 _calculate_keep_segments 函数"""
    
    def test_no_delay_cuts(self):
        """测试没有 delay cuts 的情况"""
        result = _calculate_keep_segments([], 120.0)
        assert len(result) == 1
        assert result[0] == {"start": 0.0, "end": 120.0}
    
    def test_single_delay_cut(self):
        """测试单个 delay cut"""
        delay_cuts = [
            {"start_time": 10.0, "end_time": 20.0},
        ]
        result = _calculate_keep_segments(delay_cuts, 120.0)
        
        # 应该产生两个保留片段：[0-10] 和 [20-120]
        assert len(result) == 2
        assert result[0] == {"start": 0.0, "end": 10.0}
        assert result[1] == {"start": 20.0, "end": 120.0}
    
    def test_multiple_delay_cuts(self):
        """测试多个 delay cuts"""
        delay_cuts = [
            {"start_time": 10.0, "end_time": 20.0},
            {"start_time": 50.0, "end_time": 60.0},
        ]
        result = _calculate_keep_segments(delay_cuts, 120.0)
        
        # 应该产生三个保留片段：[0-10], [20-50], [60-120]
        assert len(result) == 3
        assert result[0] == {"start": 0.0, "end": 10.0}
        assert result[1] == {"start": 20.0, "end": 50.0}
        assert result[2] == {"start": 60.0, "end": 120.0}
    
    def test_overlapping_delay_cuts(self):
        """测试重叠的 delay cuts"""
        delay_cuts = [
            {"start_time": 10.0, "end_time": 20.0},
            {"start_time": 15.0, "end_time": 25.0},  # 与第一个重叠
        ]
        result = _calculate_keep_segments(delay_cuts, 120.0)
        
        # 应该产生两个保留片段：[0-10] 和 [25-120]
        assert len(result) == 2
        assert result[0] == {"start": 0.0, "end": 10.0}
        assert result[1] == {"start": 25.0, "end": 120.0}
    
    def test_adjacent_delay_cuts(self):
        """测试相邻的 delay cuts"""
        delay_cuts = [
            {"start_time": 10.0, "end_time": 20.0},
            {"start_time": 20.0, "end_time": 30.0},  # 与第一个相邻
        ]
        result = _calculate_keep_segments(delay_cuts, 120.0)
        
        # 应该产生两个保留片段：[0-10] 和 [30-120]
        assert len(result) == 2
        assert result[0] == {"start": 0.0, "end": 10.0}
        assert result[1] == {"start": 30.0, "end": 120.0}
    
    def test_invalid_delay_cut_negative_time(self):
        """测试无效的时间值"""
        delay_cuts = [
            {"start_time": -10.0, "end_time": 20.0},
        ]
        with pytest.raises(ValueError):
            _calculate_keep_segments(delay_cuts, 120.0)
    
    def test_invalid_delay_cut_start_after_end(self):
        """测试开始时间大于结束时间"""
        delay_cuts = [
            {"start_time": 20.0, "end_time": 10.0},
        ]
        # 应该跳过无效的切割点，保留整个音频
        result = _calculate_keep_segments(delay_cuts, 120.0)
        assert len(result) == 1
        assert result[0] == {"start": 0.0, "end": 120.0}
    
    def test_delay_cut_beyond_duration(self):
        """测试超出时长的 delay cut"""
        delay_cuts = [
            {"start_time": 100.0, "end_time": 150.0},  # 超出 120s
        ]
        result = _calculate_keep_segments(delay_cuts, 120.0)
        
        # 应该产生两个保留片段：[0-100] 和 [120-120]（空）
        assert len(result) == 1
        assert result[0] == {"start": 0.0, "end": 100.0}


class TestBuildFilterComplex:
    """测试 _build_filter_complex 函数"""
    
    def test_single_segment(self):
        """测试单段"""
        keep_segments = [{"start": 10.0, "end": 20.0}]
        result = _build_filter_complex(keep_segments)
        
        assert "atrim" in result
        assert "start=10.0" in result
        assert "end=20.0" in result
        assert "[out]" in result
    
    def test_multiple_segments(self):
        """测试多段"""
        keep_segments = [
            {"start": 0.0, "end": 10.0},
            {"start": 20.0, "end": 30.0},
        ]
        result = _build_filter_complex(keep_segments)
        
        assert ";" in result  # 有分号分隔
        assert "[a0]" in result
        assert "[a1]" in result
        assert "concat" in result
        assert "n=2" in result
    
    def test_three_segments(self):
        """测试三段"""
        keep_segments = [
            {"start": 0.0, "end": 5.0},
            {"start": 10.0, "end": 15.0},
            {"start": 20.0, "end": 25.0},
        ]
        result = _build_filter_complex(keep_segments)
        
        assert "[a0][a1][a2]" in result
        assert "concat=n=3" in result


class TestGetAudioDuration:
    """测试 _get_audio_duration 函数"""
    
    @patch('src.generate_audio_b.subprocess.run')
    def test_get_duration_success(self, mock_run):
        """测试成功获取时长"""
        mock_run.return_value = Mock(
            stdout="120.5\n",
            stderr="",
            returncode=0,
        )
        
        result = _get_audio_duration("/path/to/audio.mp3")
        assert result == 120.5
    
    @patch('src.generate_audio_b.subprocess.run')
    def test_get_duration_empty_output(self, mock_run):
        """测试空输出"""
        mock_run.return_value = Mock(
            stdout="",
            stderr="error",
            returncode=0,
        )
        
        with pytest.raises(RuntimeError):
            _get_audio_duration("/path/to/audio.mp3")
    
    @patch('src.generate_audio_b.subprocess.run')
    def test_get_duration_ffprobe_error(self, mock_run):
        """测试 ffprobe 错误"""
        mock_run.side_effect = Exception("ffprobe failed")
        
        with pytest.raises(RuntimeError):
            _get_audio_duration("/path/to/audio.mp3")


class TestGenerateAudioB:
    """测试 generate_audio_b 函数"""
    
    @patch('src.generate_audio_b._get_audio_duration')
    @patch('src.generate_audio_b._run_ffmpeg_concat')
    def test_generate_audio_b_success(self, mock_run_ffmpeg, mock_get_duration):
        """测试成功生成音频 B"""
        mock_get_duration.return_value = 120.0
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_a_path = Path(tmpdir) / "audio_a.mp3"
            audio_a_path.touch()
            
            output_path = Path(tmpdir) / "audio_b.mp3"
            
            delay_cuts = [
                {"start_time": 10.0, "end_time": 20.0},
            ]
            
            result = generate_audio_b(
                str(audio_a_path),
                delay_cuts,
                str(output_path),
            )
            
            assert result == str(output_path)
            mock_run_ffmpeg.assert_called_once()
    
    @patch('src.generate_audio_b._get_audio_duration')
    def test_generate_audio_b_no_keep_segments(self, mock_get_duration):
        """测试没有保留片段的情况"""
        mock_get_duration.return_value = 120.0
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_a_path = Path(tmpdir) / "audio_a.mp3"
            audio_a_path.touch()
            
            output_path = Path(tmpdir) / "audio_b.mp3"
            
            # 覆盖整个音频的 delay cut
            delay_cuts = [
                {"start_time": 0.0, "end_time": 120.0},
            ]
            
            result = generate_audio_b(
                str(audio_a_path),
                delay_cuts,
                str(output_path),
            )
            
            # 应该生成静音音频
            assert result == str(output_path)
    
    def test_generate_audio_b_file_not_found(self):
        """测试输入文件不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audio_b.mp3"
            
            with pytest.raises(FileNotFoundError):
                generate_audio_b(
                    "/nonexistent/audio.mp3",
                    [],
                    str(output_path),
                )


class TestGenerateAudioBWithCuts:
    """测试 generate_audio_b_with_cuts 函数"""
    
    @patch('src.generate_audio_b._run_ffmpeg_concat')
    def test_generate_with_cuts_success(self, mock_run_ffmpeg):
        """测试成功生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_a_path = Path(tmpdir) / "audio_a.mp3"
            audio_a_path.touch()
            
            output_path = Path(tmpdir) / "audio_b.mp3"
            
            keep_segments = [
                {"start": 0.0, "end": 10.0},
                {"start": 20.0, "end": 30.0},
            ]
            
            result = generate_audio_b_with_cuts(
                str(audio_a_path),
                keep_segments,
                str(output_path),
            )
            
            assert result == str(output_path)
            mock_run_ffmpeg.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
