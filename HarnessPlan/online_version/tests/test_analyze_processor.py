"""
Analyze Processor 的单元测试
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.analyze_processor import (
    _collect_artifacts,
    get_delete_ranges_from_script,
)


class TestCollectArtifacts:
    """测试 _collect_artifacts 函数"""
    
    def test_collect_all_artifacts(self):
        """测试收集所有产物文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            Path(tmpdir, "task_123_ASR.Result.json").touch()
            Path(tmpdir, "task_123_原文.TXT").touch()
            Path(tmpdir, "task_123_Script1.txt").write_text("这是{删除}内容")
            Path(tmpdir, "task_123_DelayCutSegments.json").touch()
            Path(tmpdir, "task_123_audio_a.mp3").touch()
            
            result = _collect_artifacts(tmpdir, "task_123")
            
            assert "asr_result_path" in result
            assert "original_text_path" in result
            assert "script_path" in result
            assert "delay_cuts_path" in result
            assert "audio_a_path" in result
    
    def test_collect_partial_artifacts(self):
        """测试收集部分产物文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 只创建部分文件
            Path(tmpdir, "task_123_Script1.txt").touch()
            
            result = _collect_artifacts(tmpdir, "task_123")
            
            assert "script_path" in result
            assert "asr_result_path" not in result
    
    def test_collect_with_different_naming(self):
        """测试不同命名格式的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建不同命名的文件
            Path(tmpdir, "task_123_ASR.Result.json").touch()
            
            result = _collect_artifacts(tmpdir, "task_123")
            
            assert "asr_result_path" in result


class TestGetDeleteRangesFromScript:
    """测试 get_delete_ranges_from_script 函数"""
    
    def test_extract_single_range(self):
        """测试提取单个删除范围"""
        script = "这是{要删除的内容}保留的内容"
        result = get_delete_ranges_from_script(script)
        
        assert len(result) == 1
        assert result[0]["start"] == 2
        assert result[0]["end"] == 8
    
    def test_extract_multiple_ranges(self):
        """测试提取多个删除范围"""
        script = "{删除1}保留1{删除2}保留2"
        result = get_delete_ranges_from_script(script)
        
        assert len(result) == 2
        assert result[0] == {"start": 0, "end": 3}
        assert result[1] == {"start": 6, "end": 9}
    
    def test_no_delete_ranges(self):
        """测试没有删除范围"""
        script = "这是没有删除内容的文本"
        result = get_delete_ranges_from_script(script)
        
        assert result == []


class TestProcessAnalyzeIntegration:
    """测试 process_analyze 集成（使用 mock）"""
    
    @patch('src.analyze_processor.subprocess.run')
    def test_process_analyze_success(self, mock_run):
        """测试 analyze 处理成功"""
        mock_run.return_value = Mock(
            stdout="Success",
            stderr="",
            returncode=0,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir, "video.mp4")
            video_path.touch()
            reference_path = Path(tmpdir, "reference.txt")
            reference_path.write_text("标准文案")
            output_dir = Path(tmpdir, "output")
            
            # 创建模拟产物文件
            output_dir.mkdir()
            Path(output_dir, "task_123_Script1.txt").write_text("这是{删除}内容")
            
            from src.analyze_processor import process_analyze
            result = process_analyze(
                task_id="123",
                original_video_path=str(video_path),
                reference_text_path=str(reference_path),
                output_dir=str(output_dir),
                task_prefix="task_123",
            )
            
            assert result["task_id"] == "123"
            assert result["script"] == "这是{删除}内容"
            mock_run.assert_called_once()
    
    def test_process_analyze_missing_video(self):
        """测试视频文件不存在时抛出异常"""
        from src.analyze_processor import process_analyze
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                process_analyze(
                    task_id="123",
                    original_video_path="/nonexistent/video.mp4",
                    reference_text_path=str(Path(tmpdir, "ref.txt")),
                    output_dir=str(Path(tmpdir, "output")),
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
