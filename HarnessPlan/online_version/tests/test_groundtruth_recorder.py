"""
GroundTruth Recorder 的单元测试
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.groundtruth_recorder import (
    record_groundtruth,
    build_groundtruth_tos_path,
    upload_groundtruth,
    create_groundtruth_pipeline,
)


class TestRecordGroundtruth:
    """测试 record_groundtruth 函数"""
    
    def test_record_with_dict_asr(self):
        """测试使用字典作为 ASR 结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            asr_data = {"text": "测试文本", "duration": 120.5}
            
            result = record_groundtruth(
                task_id="task-123",
                company="test_company",
                reference_text="标准文案",
                original_video_url="https://tos/video.mp4",
                original_video_tos_key="videos/video.mp4",
                asr_result=asr_data,
                analyze_script="这是{删除}内容",
                edited_script="这是删除内容",
                output_dir=tmpdir,
            )
            
            # 验证文件创建
            assert Path(result["reference_path"]).exists()
            assert Path(result["analyze_script_path"]).exists()
            assert Path(result["edited_script_path"]).exists()
            assert Path(result["asr_result_path"]).exists()
            assert Path(result["metadata_path"]).exists()
            
            # 验证 ASR 内容
            with open(result["asr_result_path"], "r", encoding="utf-8") as f:
                saved_asr = json.load(f)
            assert saved_asr["text"] == "测试文本"
            assert saved_asr["duration"] == 120.5
    
    def test_record_with_file_asr(self):
        """测试使用文件路径作为 ASR 结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 ASR 文件
            asr_file = Path(tmpdir) / "asr_source.json"
            asr_data = {"text": "来自文件的文本"}
            with open(asr_file, "w", encoding="utf-8") as f:
                json.dump(asr_data, f)
            
            output_dir = Path(tmpdir) / "groundtruth"
            
            result = record_groundtruth(
                task_id="task-123",
                company="test_company",
                reference_text="标准文案",
                original_video_url="https://tos/video.mp4",
                original_video_tos_key="videos/video.mp4",
                asr_result=str(asr_file),
                analyze_script="分析脚本",
                edited_script="编辑脚本",
                output_dir=str(output_dir),
            )
            
            # 验证 ASR 内容被复制
            with open(result["asr_result_path"], "r", encoding="utf-8") as f:
                saved_asr = json.load(f)
            assert saved_asr["text"] == "来自文件的文本"
    
    def test_metadata_content(self):
        """测试 metadata.json 内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = record_groundtruth(
                task_id="task-456",
                company="test_company",
                reference_text="标准文案内容",
                original_video_url="https://tos/video2.mp4",
                original_video_tos_key="videos/video2.mp4",
                asr_result={},
                analyze_script="分析脚本",
                edited_script="编辑脚本",
                output_dir=tmpdir,
                timestamp=datetime(2024, 4, 1, 12, 0, 0),
            )
            
            with open(result["metadata_path"], "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            assert metadata["task_id"] == "task-456"
            assert metadata["company"] == "test_company"
            assert metadata["reference_text"] == "标准文案内容"
            assert metadata["original_video_url"] == "https://tos/video2.mp4"
            assert metadata["analyze_script"] == "分析脚本"
            assert metadata["edited_script"] == "编辑脚本"


class TestBuildGroundtruthTosPath:
    """测试 build_groundtruth_tos_path 函数"""
    
    def test_path_format(self):
        """测试路径格式"""
        timestamp = datetime(2024, 4, 15, 10, 30, 45)
        path = build_groundtruth_tos_path("test_company", timestamp)
        
        assert path.startswith("cujian_input_data/test_company/2024-04/cujian_userdata_")
        assert "20240415_103045" in path
    
    def test_default_timestamp(self):
        """测试默认时间戳"""
        path = build_groundtruth_tos_path("test_company")
        assert "cujian_input_data/test_company/" in path


class TestUploadGroundtruth:
    """测试 upload_groundtruth 函数"""
    
    def test_upload_all_files(self):
        """测试上传所有文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            for filename in ["reference.txt", "analyze_script.txt", "edited_script.txt", 
                           "asr_result.json", "metadata.json"]:
                Path(tmpdir, filename).write_text(f"content of {filename}")
            
            # Mock 上传函数
            def mock_upload(local_path, object_key):
                return f"https://tos.example.com/{object_key}"
            
            result = upload_groundtruth(
                local_dir=tmpdir,
                tos_prefix="cujian_input_data/test/2024-04/test_dir",
                upload_fn=mock_upload,
            )
            
            assert result["tos_prefix"] == "cujian_input_data/test/2024-04/test_dir"
            assert len(result["uploaded_files"]) == 5
            
            # 验证 metadata.json 的 URL
            metadata_info = result["uploaded_files"]["metadata.json"]
            assert "metadata.json" in metadata_info["key"]
            assert metadata_info["url"].startswith("https://")


class TestCreateGroundtruthPipeline:
    """测试 create_groundtruth_pipeline 函数"""
    
    def test_pipeline_downloads_asr(self):
        """测试 pipeline 会下载 ASR 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 准备 ASR 数据
            asr_data = {"text": "真实ASR内容", "segments": []}
            
            # Mock 下载函数
            def mock_download(url, local_path):
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(asr_data, f)
                return local_path
            
            # Mock 上传函数
            def mock_upload(local_path, object_key):
                return f"https://tos.example.com/{object_key}"
            
            result = create_groundtruth_pipeline(
                task_id="task-789",
                company="test_company",
                reference_text="标准文案",
                original_video_url="https://tos/video.mp4",
                original_video_tos_key="videos/video.mp4",
                asr_result_url="https://tos/asr.json",
                analyze_script="这是{删除}内容",
                edited_script="这是删除内容",
                work_dir=tmpdir,
                upload_fn=mock_upload,
                download_fn=mock_download,
            )
            
            # 验证 ASR 被下载并保存
            local_dir = Path(result["local_dir"])
            asr_path = local_dir / "asr_result.json"
            assert asr_path.exists()
            
            with open(asr_path, "r", encoding="utf-8") as f:
                saved_asr = json.load(f)
            assert saved_asr["text"] == "真实ASR内容"
    
    def test_pipeline_returns_correct_fields(self):
        """测试 pipeline 返回正确的字段名（与模型一致）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            def mock_download(url, local_path):
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                return local_path
            
            def mock_upload(local_path, object_key):
                return f"https://tos.example.com/{object_key}"
            
            result = create_groundtruth_pipeline(
                task_id="task-999",
                company="test_company",
                reference_text="标准文案",
                original_video_url="https://tos/video.mp4",
                original_video_tos_key="videos/video.mp4",
                asr_result_url="https://tos/asr.json",
                analyze_script="分析脚本",
                edited_script="编辑脚本",
                work_dir=tmpdir,
                upload_fn=mock_upload,
                download_fn=mock_download,
            )
            
            # 验证返回字段与模型定义一致，且语义是 GroundTruth 目录前缀
            assert "success" in result
            assert "groundtruth_url" in result  # 不是 metadata_url
            assert "groundtruth_tos_key" in result  # 不是 metadata_key
            assert result["success"] is True
            expected_prefix = result["tos_prefix"]
            assert result["groundtruth_url"] == expected_prefix
            assert result["groundtruth_tos_key"] == expected_prefix
            assert result["groundtruth_url"].startswith("cujian_input_data/")
    
    def test_pipeline_handles_download_failure(self):
        """测试 pipeline 处理下载失败的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock 下载函数 - 模拟失败
            def mock_download_fail(url, local_path):
                raise Exception("Download failed")
            
            def mock_upload(local_path, object_key):
                return f"https://tos.example.com/{object_key}"
            
            result = create_groundtruth_pipeline(
                task_id="task-000",
                company="test_company",
                reference_text="标准文案",
                original_video_url="https://tos/video.mp4",
                original_video_tos_key="videos/video.mp4",
                asr_result_url="https://tos/asr.json",
                analyze_script="分析脚本",
                edited_script="编辑脚本",
                work_dir=tmpdir,
                upload_fn=mock_upload,
                download_fn=mock_download_fail,
            )
            
            # 即使 ASR 下载失败，也应该继续执行
            assert result["success"] is True
            
            # ASR 应该保存为空对象
            asr_path = Path(result["local_dir"]) / "asr_result.json"
            with open(asr_path, "r", encoding="utf-8") as f:
                asr_data = json.load(f)
            assert asr_data == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
