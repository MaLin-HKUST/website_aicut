"""GroundTruth Service - GroundTruth 生成和上传服务 (F22)

提供 GroundTruth 记录和上传功能：
1. 生成 GroundTruth 目录结构
2. 收集和整理训练数据
3. 上传到 TOS
4. 记录上传状态（不阻塞主流程）

目录结构:
cujian_input_data/{company}/{year-month}/cujian_userdata_{timestamp}/
    ├── reference.txt          # 参考文案
    ├── analyze_script.txt     # 分析生成的脚本
    ├── edited_script.txt      # 用户编辑后的脚本
    ├── asr_result.json        # ASR 识别结果
    ├── final_video.mp4        # 最终视频（可选）
    └── metadata.json          # 元数据
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)


class GroundTruthRecorder:
    """GroundTruth 记录器
    
    负责收集和整理训练数据，生成标准化的 GroundTruth 目录。
    """
    
    # 默认公司标识
    DEFAULT_COMPANY = "default"
    
    # TOS bucket 名称
    BUCKET = "smart-cut"
    
    def __init__(
        self,
        tos_service: Any,
        company: Optional[str] = None,
        include_video: bool = False
    ):
        """初始化 GroundTruth 记录器
        
        Args:
            tos_service: TOS 服务对象
            company: 公司标识，用于目录组织
            include_video: 是否包含最终视频文件
        """
        self.tos_service = tos_service
        self.company = company or self.DEFAULT_COMPANY
        self.include_video = include_video
    
    def record(
        self,
        task_id: str,
        edit_id: str,
        reference_text: Optional[str] = None,
        analyze_script: Optional[dict] = None,
        edited_script: Optional[dict] = None,
        asr_result: Optional[dict] = None,
        final_video_path: Optional[Path] = None,
        work_dir: Optional[Path] = None,
        extra_metadata: Optional[dict] = None
    ) -> Path:
        """生成 GroundTruth 目录
        
        Args:
            task_id: 业务任务ID
            edit_id: 编辑记录ID
            reference_text: 参考文案
            analyze_script: 分析生成的脚本
            edited_script: 用户编辑后的脚本
            asr_result: ASR 识别结果
            final_video_path: 最终视频路径（可选）
            work_dir: 工作目录
            extra_metadata: 额外元数据
            
        Returns:
            Path: GroundTruth 目录路径
        """
        # 创建目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gt_dir = self._create_gt_directory(work_dir, timestamp)
        
        # 写入数据文件
        if reference_text:
            self._write_text_file(gt_dir / "reference.txt", reference_text)
        
        if analyze_script:
            self._write_json_file(gt_dir / "analyze_script.txt", analyze_script)
        
        if edited_script:
            self._write_json_file(gt_dir / "edited_script.txt", edited_script)
        
        if asr_result:
            self._write_json_file(gt_dir / "asr_result.json", asr_result)
        
        # 复制最终视频（如果需要）
        if self.include_video and final_video_path and final_video_path.exists():
            shutil.copy2(final_video_path, gt_dir / "final_video.mp4")
        
        # 写入元数据
        metadata = self._create_metadata(
            task_id=task_id,
            edit_id=edit_id,
            timestamp=timestamp,
            extra=extra_metadata
        )
        self._write_json_file(gt_dir / "metadata.json", metadata)
        
        logger.info(f"GroundTruth recorded: {gt_dir}")
        return gt_dir
    
    def _create_gt_directory(self, work_dir: Optional[Path], timestamp: str) -> Path:
        """创建 GroundTruth 目录
        
        Args:
            work_dir: 工作目录
            timestamp: 时间戳
            
        Returns:
            Path: GroundTruth 目录路径
        """
        if work_dir is None:
            work_dir = Path("/tmp/groundtruth")
        
        gt_dir = work_dir / "groundtruth" / f"cujian_userdata_{timestamp}"
        gt_dir.mkdir(parents=True, exist_ok=True)
        
        return gt_dir
    
    def _write_text_file(self, path: Path, content: str) -> None:
        """写入文本文件"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _write_json_file(self, path: Path, data: dict) -> None:
        """写入 JSON 文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _create_metadata(
        self,
        task_id: str,
        edit_id: str,
        timestamp: str,
        extra: Optional[dict] = None
    ) -> dict:
        """创建元数据"""
        metadata = {
            "task_id": task_id,
            "edit_id": edit_id,
            "company": self.company,
            "created_at": datetime.now().isoformat(),
            "timestamp": timestamp,
            "version": "1.0",
        }
        
        if extra:
            metadata.update(extra)
        
        return metadata
    
    async def upload(self, gt_dir: Path, task_id: Optional[str] = None) -> Optional[str]:
        """上传 GroundTruth 到 TOS
        
        Args:
            gt_dir: GroundTruth 目录路径
            task_id: 业务任务ID（用于日志）
            
        Returns:
            str: TOS URL，上传失败返回 None
        """
        if not gt_dir.exists():
            logger.error(f"GroundTruth directory not found: {gt_dir}")
            return None
        
        try:
            # 构建上传路径
            year_month = datetime.now().strftime("%Y-%m")
            gt_name = gt_dir.name
            base_key = f"cujian_input_data/{self.company}/{year_month}/{gt_name}"
            
            # 上传所有文件
            uploaded_files = []
            failed_files = []
            for file_path in gt_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(gt_dir)
                    key = f"{base_key}/{relative_path}"
                    
                    if self._upload_file(file_path, key):
                        uploaded_files.append(key)
                    else:
                        failed_files.append(key)
            
            # 如果有文件上传失败，返回 None
            if failed_files:
                logger.error(f"GroundTruth upload partially failed: {len(failed_files)} files failed")
                return None
            
            logger.info(f"GroundTruth uploaded: {base_key}, files={len(uploaded_files)}")
            return base_key
            
        except Exception as e:
            logger.error(f"Failed to upload GroundTruth: {e}")
            return None
    
    def _upload_file(self, local_path: Path, key: str) -> bool:
        """上传单个文件到 TOS
        
        Args:
            local_path: 本地文件路径
            key: TOS key
            
        Returns:
            bool: 是否成功
        """
        if not self.tos_service:
            logger.warning("TOS service not available, using mock upload")
            # Mock upload: 复制到本地目录
            dest = Path(f"/tmp/fake_tos/{self.BUCKET}") / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
            return True
        
        if not hasattr(self.tos_service, 'upload_file'):
            logger.error("TOS service does not have upload_file method")
            return False
        
        try:
            result = self.tos_service.upload_file(
                bucket=self.BUCKET,
                key=key,
                file_path=str(local_path)
            )
            
            if result.success:
                return True
            else:
                logger.error(f"Upload failed for {key}: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Exception during upload {key}: {e}")
            return False


class GroundTruthService:
    """GroundTruth 服务
    
    高层服务接口，整合记录和上传功能。
    支持异步上传，不阻塞主流程。
    """
    
    def __init__(
        self,
        tos_service: Any,
        company: Optional[str] = None,
        include_video: bool = False
    ):
        """初始化 GroundTruth 服务
        
        Args:
            tos_service: TOS 服务对象
            company: 公司标识
            include_video: 是否包含视频
        """
        self.recorder = GroundTruthRecorder(
            tos_service=tos_service,
            company=company,
            include_video=include_video
        )
        self.upload_results: dict[str, Any] = {}
    
    async def record_and_upload(
        self,
        task_id: str,
        edit_id: str,
        reference_text: Optional[str] = None,
        analyze_script: Optional[dict] = None,
        edited_script: Optional[dict] = None,
        asr_result: Optional[dict] = None,
        final_video_path: Optional[Path] = None,
        work_dir: Optional[Path] = None,
        extra_metadata: Optional[dict] = None
    ) -> dict[str, Any]:
        """记录并上传 GroundTruth
        
        这是一个完整的流程，包括记录和上传。
        上传失败不会抛出异常，而是记录在结果中。
        
        Args:
            task_id: 业务任务ID
            edit_id: 编辑记录ID
            reference_text: 参考文案
            analyze_script: 分析脚本
            edited_script: 编辑后的脚本
            asr_result: ASR 结果
            final_video_path: 最终视频路径
            work_dir: 工作目录
            extra_metadata: 额外元数据
            
        Returns:
            dict: 操作结果
                - success: 是否成功
                - gt_dir: 本地目录路径
                - gt_url: TOS URL（可能为 None）
                - error: 错误信息（如果有）
        """
        result = {
            "success": False,
            "gt_dir": None,
            "gt_url": None,
            "error": None,
        }
        
        try:
            # 1. 记录 GroundTruth
            gt_dir = self.recorder.record(
                task_id=task_id,
                edit_id=edit_id,
                reference_text=reference_text,
                analyze_script=analyze_script,
                edited_script=edited_script,
                asr_result=asr_result,
                final_video_path=final_video_path,
                work_dir=work_dir,
                extra_metadata=extra_metadata
            )
            result["gt_dir"] = str(gt_dir)
            
            # 2. 上传到 TOS（失败不阻塞）
            try:
                gt_url = await self.recorder.upload(gt_dir, task_id)
                result["gt_url"] = gt_url
                if gt_url is None:
                    # 上传失败
                    result["error"] = "Upload failed: some files could not be uploaded"
                result["success"] = True
            except Exception as e:
                logger.warning(f"GroundTruth upload failed (non-blocking): {e}")
                result["error"] = f"Upload failed: {e}"
                # 记录成功，上传失败，整体不算失败
                result["success"] = True
            
        except Exception as e:
            logger.error(f"GroundTruth recording failed: {e}")
            result["error"] = str(e)
        
        # 记录结果
        self.upload_results[task_id] = result
        
        return result
    
    def record_only(
        self,
        task_id: str,
        edit_id: str,
        reference_text: Optional[str] = None,
        analyze_script: Optional[dict] = None,
        edited_script: Optional[dict] = None,
        asr_result: Optional[dict] = None,
        final_video_path: Optional[Path] = None,
        work_dir: Optional[Path] = None,
        extra_metadata: Optional[dict] = None
    ) -> Path:
        """仅记录 GroundTruth，不上传
        
        用于延后上传的场景。
        
        Returns:
            Path: GroundTruth 目录路径
        """
        return self.recorder.record(
            task_id=task_id,
            edit_id=edit_id,
            reference_text=reference_text,
            analyze_script=analyze_script,
            edited_script=edited_script,
            asr_result=asr_result,
            final_video_path=final_video_path,
            work_dir=work_dir,
            extra_metadata=extra_metadata
        )
    
    async def upload_recorded(
        self,
        gt_dir: Path,
        task_id: Optional[str] = None
    ) -> Optional[str]:
        """上传已记录的 GroundTruth
        
        Args:
            gt_dir: GroundTruth 目录路径
            task_id: 业务任务ID
            
        Returns:
            str: TOS URL，失败返回 None
        """
        return await self.recorder.upload(gt_dir, task_id)
    
    def get_upload_status(self, task_id: str) -> Optional[dict]:
        """获取上传状态
        
        Args:
            task_id: 业务任务ID
            
        Returns:
            dict: 上传结果，未找到返回 None
        """
        return self.upload_results.get(task_id)


# 便捷函数
def create_groundtruth_service(
    tos_service: Any,
    company: Optional[str] = None
) -> GroundTruthService:
    """创建 GroundTruth 服务的工厂函数
    
    Args:
        tos_service: TOS 服务对象
        company: 公司标识
        
    Returns:
        GroundTruthService: GroundTruth 服务实例
    """
    return GroundTruthService(
        tos_service=tos_service,
        company=company,
        include_video=False  # 默认不包含视频，减小体积
    )
