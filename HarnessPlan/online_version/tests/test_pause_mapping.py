"""
暂停映射模块的单元测试
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.pause_mapping import (
    map_pauses_to_original_seconds,
    dump_pause_cuts_for_direct_cutter,
    load_pause_cuts_from_audio_a,
    map_pauses_from_audio_a_file,
)


class TestMapPausesToOriginalSeconds:
    """测试 map_pauses_to_original_seconds 函数"""
    
    def test_no_pause_cuts(self):
        """测试没有 pause cuts 的情况"""
        result = map_pauses_to_original_seconds([], [])
        assert result == []
    
    def test_no_delay_cuts(self):
        """测试没有 delay cuts 的情况（直接映射）"""
        pause_cuts = [
            {"start_time": 5.0, "end_time": 6.5},
        ]
        result = map_pauses_to_original_seconds(pause_cuts, [])
        assert len(result) == 1
        assert result[0]["start_time"] == 5.0
        assert result[0]["end_time"] == 6.5
        assert result[0]["type"] == "pause"
    
    def test_single_delay_cut(self):
        """测试单个 delay cut 的情况"""
        # delay cut: 10s - 12s（2秒延迟）
        # pause on audio_a: 5s - 6.5s
        # 映射回原视频: 5s + 0s = 5s, 6.5s + 0s = 6.5s
        # 因为 pause 在 delay 之前，所以不受影响
        pause_cuts = [
            {"start_time": 5.0, "end_time": 6.5},
        ]
        delay_cuts = [
            {"start_time": 10.0, "end_time": 12.0},
        ]
        result = map_pauses_to_original_seconds(pause_cuts, delay_cuts)
        assert len(result) == 1
        assert result[0]["start_time"] == 5.0
        assert result[0]["end_time"] == 6.5
    
    def test_delay_before_pause(self):
        """测试 delay cut 在 pause 之前的情况"""
        # delay cut: 2s - 4s（2秒延迟）
        # pause on audio_a: 5s - 6s
        # audio_a 的 5s 对应原视频的 5s + 2s = 7s
        pause_cuts = [
            {"start_time": 5.0, "end_time": 6.0},
        ]
        delay_cuts = [
            {"start_time": 2.0, "end_time": 4.0},
        ]
        result = map_pauses_to_original_seconds(pause_cuts, delay_cuts)
        assert len(result) == 1
        assert result[0]["start_time"] == 7.0  # 5.0 + 2.0
        assert result[0]["end_time"] == 8.0    # 6.0 + 2.0
    
    def test_multiple_delay_cuts(self):
        """测试多个 delay cuts 的情况"""
        # delay cuts: [2-4] + [6-8] = 总延迟 4秒
        # pause on audio_a: 10s - 11s
        # 两个 delay 都在 pause 之前，所以总延迟 4秒
        pause_cuts = [
            {"start_time": 10.0, "end_time": 11.0},
        ]
        delay_cuts = [
            {"start_time": 2.0, "end_time": 4.0},
            {"start_time": 6.0, "end_time": 8.0},
        ]
        result = map_pauses_to_original_seconds(pause_cuts, delay_cuts)
        assert len(result) == 1
        assert result[0]["start_time"] == 14.0  # 10.0 + 4.0
        assert result[0]["end_time"] == 15.0    # 11.0 + 4.0
    
    def test_pause_between_delays(self):
        """测试 pause 在两个 delay cuts 之间的情况"""
        # delay cuts: [2-4] + [8-10]
        # pause on audio_a: 5s - 5.9s（在第一个 delay 之后，第二个之前）
        # 应该只加上第一个 delay 的 2秒
        pause_cuts = [
            {"start_time": 5.0, "end_time": 5.9},
        ]
        delay_cuts = [
            {"start_time": 2.0, "end_time": 4.0},
            {"start_time": 8.0, "end_time": 10.0},
        ]
        result = map_pauses_to_original_seconds(pause_cuts, delay_cuts)
        assert len(result) == 1
        assert result[0]["start_time"] == 7.0  # 5.0 + 2.0
        assert result[0]["end_time"] == 7.9    # 5.9 + 2.0


class TestDumpPauseCutsForDirectCutter:
    """测试 dump_pause_cuts_for_direct_cutter 函数"""
    
    def test_empty_pauses(self):
        """测试空列表"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        
        try:
            result = dump_pause_cuts_for_direct_cutter([], path)
            assert result == path
            
            with open(path, 'r') as f:
                data = json.load(f)
            assert data == {"cut_segments": []}
        finally:
            Path(path).unlink()
    
    def test_single_pause(self):
        """测试单个 pause"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        
        try:
            pauses = [
                {"start_time": 5.0, "end_time": 6.5, "type": "pause"},
            ]
            result = dump_pause_cuts_for_direct_cutter(pauses, path)
            assert result == path
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            assert len(data["cut_segments"]) == 1
            assert data["cut_segments"][0]["start_time"] == 5000  # 毫秒
            assert data["cut_segments"][0]["end_time"] == 6500
            assert data["cut_segments"][0]["type"] == "pause"
            assert data["cut_segments"][0]["position"] == ""
        finally:
            Path(path).unlink()
    
    def test_multiple_pauses(self):
        """测试多个 pauses"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        
        try:
            pauses = [
                {"start_time": 1.0, "end_time": 2.0},
                {"start_time": 5.5, "end_time": 6.5},
            ]
            dump_pause_cuts_for_direct_cutter(pauses, path)
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            assert len(data["cut_segments"]) == 2
            assert data["cut_segments"][0]["start_time"] == 1000
            assert data["cut_segments"][1]["start_time"] == 5500
        finally:
            Path(path).unlink()


class TestLoadPauseCutsFromAudioA:
    """测试 load_pause_cuts_from_audio_a 函数"""
    
    def test_load_list_format(self):
        """测试列表格式"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
            json.dump([
                {"start_time": 1.0, "end_time": 2.0},
            ], f)
        
        try:
            result = load_pause_cuts_from_audio_a(path)
            assert len(result) == 1
            assert result[0]["start_time"] == 1.0
        finally:
            Path(path).unlink()
    
    def test_load_cut_segments_format_seconds(self):
        """测试 cut_segments 格式（秒级）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
            json.dump({
                "cut_segments": [
                    {"start_time": 1.0, "end_time": 2.0},
                ]
            }, f)
        
        try:
            result = load_pause_cuts_from_audio_a(path)
            assert len(result) == 1
            assert result[0]["start_time"] == 1.0
        finally:
            Path(path).unlink()
    
    def test_load_cut_segments_format_milliseconds(self):
        """测试 cut_segments 格式（毫秒级）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
            json.dump({
                "cut_segments": [
                    {"start_time": 1000, "end_time": 2000},
                ]
            }, f)
        
        try:
            result = load_pause_cuts_from_audio_a(path)
            assert len(result) == 1
            assert result[0]["start_time"] == 1.0  # 转换为秒
        finally:
            Path(path).unlink()


class TestMapPausesFromAudioAFile:
    """测试 map_pauses_from_audio_a_file 函数"""
    
    def test_full_pipeline(self):
        """测试完整流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建输入文件
            pause_path = Path(tmpdir) / "pause_cuts.json"
            delay_path = Path(tmpdir) / "delay_cuts.json"
            output_path = Path(tmpdir) / "output.json"
            
            with open(pause_path, 'w') as f:
                json.dump([
                    {"start_time": 5.0, "end_time": 6.0},
                ], f)
            
            with open(delay_path, 'w') as f:
                json.dump([
                    {"start_time": 2.0, "end_time": 4.0},
                ], f)
            
            # 执行映射
            result = map_pauses_from_audio_a_file(
                str(pause_path),
                str(delay_path),
                str(output_path),
            )
            
            assert result == str(output_path)
            
            # 验证输出
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert len(data["cut_segments"]) == 1
            assert data["cut_segments"][0]["start_time"] == 7000  # 5.0 + 2.0 = 7.0s = 7000ms
            assert data["cut_segments"][0]["end_time"] == 8000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
