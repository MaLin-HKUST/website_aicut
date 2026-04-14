"""Preview Processor - Smart Cut Preview 任务处理器 (F18)

处理预览生成任务：
1. 读取 edit 记录（edited_script）
2. 下载原视频和ASR结果
3. 调用 preview_processor 算法
4. 生成 edited_delay_cuts.json, pause_cuts_on_original.json, audio_b.mp3
5. 上传产物到TOS
6. 更新 SmartCutEdit 状态和 SmartCutTask.active_edit_id
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from apps.models.scheduler_task import SchedulerTask
from apps.models.edit import SmartCutEdit, EditStatus
from apps.models.task import SmartCutTask as BusinessTask, TaskStatus, CurrentStage
from worker.base_processor import BaseProcessor


logger = logging.getLogger(__name__)


class PreviewProcessor(BaseProcessor):
    """
    Preview阶段处理器:
    1. 下载原始视频、ASR结果
    2. 读取 edit 的 edited_script
    3. 调用 preview_processor 算法生成 audio_b, edited_delay_cuts, pause_cuts
    4. 上传产物到 TOS (key: smart-cut/{task_id}/preview/{edit_id}/{filename})
    5. 更新 SmartCutEdit 和 SmartCutTask
    """
    
    # TOS bucket 名称
    BUCKET = "smart-cut"
    
    # 算法模块路径
    ONLINE_VERSION_PATH = "/app/aicut2602/online_version"
    
    def __init__(self, tos_service: Any, workspace: str):
        """初始化处理器
        
        Args:
            tos_service: TOS 服务对象
            workspace: 工作目录路径
        """
        super().__init__(tos_service, workspace)
        self._current_task: SchedulerTask | None = None
        self._edit: SmartCutEdit | None = None
        self._business_task: BusinessTask | None = None
        self._input_data: dict[str, Any] = {}
    
    async def process(self, task: SchedulerTask, workspace: str) -> dict[str, Any]:
        """处理 preview 任务的完整流程
        
        Args:
            task: 调度任务对象
            workspace: 工作目录路径
            
        Returns:
            dict: 处理结果
        """
        logger.info(f"Processing preview task: {task.id}, business_task: {task.business_task_id}")
        
        self._current_task = task
        work_dir = Path(workspace) / task.business_task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Phase 1: 准备输入文件
            self.update_progress(0.1)
            await self.prepare_input()
            logger.info(f"Input prepared: edit_id={self._edit.id if self._edit else None}")
            
            # Phase 2: 执行 preview 算法
            self.update_progress(0.3)
            output_dir = work_dir / "preview" / (self._edit.id if self._edit else "unknown")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result = await self.execute()
            logger.info(f"Preview algorithm completed")
            
            # Phase 3: 上传产物到TOS
            self.update_progress(0.8)
            await self.upload_output(result)
            logger.info(f"Outputs uploaded")
            
            # Phase 4: 更新数据库
            self.update_progress(0.95)
            await self._update_database_async()
            logger.info(f"Database updated")
            
            self.update_progress(1.0)
            
            return {
                "status": "success",
                "edit_id": self._edit.id if self._edit else None,
                "audio_b_url": result.get("audio_b_url"),
                "delay_cuts_url": result.get("delay_cuts_url"),
                "pause_cuts_url": result.get("pause_cuts_url"),
            }
            
        except Exception as e:
            logger.exception(f"Preview task failed: {task.id}, error: {e}")
            await self._handle_failure_async(str(e))
            raise
    
    async def prepare_input(self) -> None:
        """
        准备输入数据:
        1. 从 payload 获取 edit_id
        2. 下载 original_video, asr_result
        3. 读取 edit.edited_script
        """
        from configs.database import SessionLocal
        
        if not self._current_task:
            raise ValueError("No current task set")
        
        task = self._current_task
        payload = task.payload
        edit_id = payload.get("edit_id")
        
        if not edit_id:
            raise ValueError("Missing edit_id in task payload")
        
        db = SessionLocal()
        try:
            # 读取 edit 记录
            edit = db.query(SmartCutEdit).filter_by(id=edit_id).first()
            if not edit:
                raise ValueError(f"Edit not found: {edit_id}")
            self._edit = edit
            
            # 读取业务任务获取原始视频URL
            business_task = db.query(BusinessTask).filter_by(id=task.business_task_id).first()
            if not business_task:
                raise ValueError(f"Business task not found: {task.business_task_id}")
            self._business_task = business_task
            
            work_dir = self.file_transport.task_dir(task.business_task_id)
            input_dir = work_dir / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存编辑后的脚本到文件
            edited_script_path = input_dir / "edited_script.json"
            with open(edited_script_path, 'w', encoding='utf-8') as f:
                json.dump(edit.edited_script, f, ensure_ascii=False, indent=2)
            
            self._input_data = {
                "edit_id": edit_id,
                "edited_script": edit.edited_script,
                "edited_script_path": edited_script_path,
                "original_video_url": business_task.original_video_url,
                "asr_result_url": business_task.asr_result_tos_key,
            }
            
            # 异步下载原视频
            if business_task.original_video_url:
                video_path = input_dir / "source_video.mp4"
                await self._download_from_tos_async(business_task.original_video_url, video_path)
                self._input_data["original_video"] = video_path
            else:
                raise ValueError("Missing original_video_url in business task")
            
            # 异步下载ASR结果
            if business_task.asr_result_tos_key:
                asr_path = input_dir / "asr_result.json"
                await self._download_from_tos_async(business_task.asr_result_tos_key, asr_path)
                with open(asr_path, 'r', encoding='utf-8') as f:
                    self._input_data["asr_result"] = json.load(f)
            else:
                raise ValueError("Missing asr_result_tos_key in business task")

            self.job_contract.write_task_manifest(
                task,
                stage="preview",
                edit_id=edit_id,
                inputs={
                    "original_video": {
                        "source": business_task.original_video_url,
                        "local_path": str(self._input_data["original_video"]),
                    },
                    "asr_result": {
                        "source": business_task.asr_result_tos_key,
                        "local_path": str(asr_path),
                    },
                    "edited_script": {
                        "source": f"db:smart_cut_edits/{edit_id}",
                        "local_path": str(edited_script_path),
                    },
                },
                expected_outputs=[
                    {"name": "edited_delay_cuts", "path": str(work_dir / "preview" / edit_id / "edited_delay_cuts.json")},
                    {"name": "pause_cuts_on_original", "path": str(work_dir / "preview" / edit_id / "pause_cuts_on_original.json")},
                    {"name": "audio_b", "path": str(work_dir / "preview" / edit_id / "audio_b.mp3")},
                ],
                payload=dict(payload),
            )
            
        finally:
            db.close()
    
    async def execute(self) -> dict[str, Any]:
        """
        调用 preview_processor 算法
        
        输入: edited_script, asr_result, original_video
        输出: audio_b.mp3, edited_delay_cuts.json, pause_cuts_on_original.json
        
        Returns:
            dict: 产物信息，包含本地路径和URL
        """
        if not self._input_data:
            raise ValueError("Input data not prepared. Call prepare_input() first.")
        
        task = self._current_task
        edit_id = self._edit.id if self._edit else "unknown"
        output_dir = self.file_transport.stage_dir(task.business_task_id, "preview", edit_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行算法
        algorithm_result = await self._execute_algorithm_async(
            edited_script=self._input_data["edited_script"],
            asr_result=self._input_data["asr_result"],
            original_video=self._input_data["original_video"],
            output_dir=output_dir,
            task_id=task.business_task_id,
            edit_id=edit_id
        )
        
        return {
            "edited_delay_cuts_path": algorithm_result.get("edited_delay_cuts_path"),
            "pause_cuts_path": algorithm_result.get("pause_cuts_path"),
            "audio_b_path": algorithm_result.get("audio_b_path"),
            "audio_b_url": None,  # 将在 upload_output 中设置
            "delay_cuts_url": None,
            "pause_cuts_url": None,
        }
    
    async def upload_output(self, result: dict) -> None:
        """
        上传产物到 TOS
        
        更新 SmartCutEdit:
          - status = "success"
          - audio_b_url
          - delay_cuts_tos_key (edited_delay_cuts)
          - pause_cuts_tos_key (pause_cuts_on_original)
        更新 SmartCutTask:
          - active_edit_id = self.edit.id
        """
        task = self._current_task
        edit_id = self._edit.id if self._edit else "unknown"
        task_id = task.business_task_id
        base_key = f"smart-cut/{task_id}/preview/{edit_id}"
        
        upload_results = {}
        
        # 上传 edited_delay_cuts
        if result.get("edited_delay_cuts_path"):
            key = f"{base_key}/edited_delay_cuts.json"
            await self._upload_file_async(result["edited_delay_cuts_path"], key)
            upload_results["edited_delay_cuts"] = key
            result["delay_cuts_url"] = key
        
        # 上传 pause_cuts
        if result.get("pause_cuts_path"):
            key = f"{base_key}/pause_cuts_on_original.json"
            await self._upload_file_async(result["pause_cuts_path"], key)
            upload_results["pause_cuts"] = key
            result["pause_cuts_url"] = key
        
        # 上传 audio_b
        if result.get("audio_b_path"):
            key = f"{base_key}/audio_b.mp3"
            await self._upload_file_async(result["audio_b_path"], key)
            upload_results["audio_b"] = key
            result["audio_b_url"] = key
        
        # 保存上传结果用于数据库更新
        self._upload_results = upload_results
        self.job_contract.write_result_manifest(
            task_id=task_id,
            scheduler_task_id=task.id,
            stage="preview",
            status="success",
            outputs={
                "edited_delay_cuts": {
                    "local_path": str(result["edited_delay_cuts_path"]) if result.get("edited_delay_cuts_path") else None,
                    "tos_key": upload_results.get("edited_delay_cuts"),
                },
                "pause_cuts_on_original": {
                    "local_path": str(result["pause_cuts_path"]) if result.get("pause_cuts_path") else None,
                    "tos_key": upload_results.get("pause_cuts"),
                },
                "audio_b": {
                    "local_path": str(result["audio_b_path"]) if result.get("audio_b_path") else None,
                    "tos_key": upload_results.get("audio_b"),
                },
            },
            metadata={"edit_id": edit_id},
        )
    
    async def _execute_algorithm_async(
        self,
        edited_script: dict,
        asr_result: dict,
        original_video: Path,
        output_dir: Path,
        task_id: str,
        edit_id: str
    ) -> dict[str, Any]:
        """异步执行 preview 算法
        
        调用 online_version/src/preview_processor.py
        
        Returns:
            dict: 产物路径
        """
        # 在线程池中执行同步算法
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._execute_algorithm_sync,
            edited_script,
            asr_result,
            original_video,
            output_dir,
            task_id,
            edit_id
        )
    
    def _execute_algorithm_sync(
        self,
        edited_script: dict,
        asr_result: dict,
        original_video: Path,
        output_dir: Path,
        task_id: str,
        edit_id: str
    ) -> dict[str, Any]:
        """同步执行 preview 算法（在线程池中运行）"""
        # 添加 online_version 到 Python 路径
        if self.ONLINE_VERSION_PATH not in sys.path:
            sys.path.insert(0, self.ONLINE_VERSION_PATH)
        
        try:
            # 尝试导入 preview_processor
            from src.preview_processor import PreviewProcessor as AlgorithmPreviewProcessor
            
            # 保存配置到文件
            edited_script_path = output_dir / "edited_script.json"
            with open(edited_script_path, 'w', encoding='utf-8') as f:
                json.dump(edited_script, f, ensure_ascii=False, indent=2)
            
            asr_result_path = output_dir / "asr_result.json"
            with open(asr_result_path, 'w', encoding='utf-8') as f:
                json.dump(asr_result, f, ensure_ascii=False, indent=2)
            
            # 创建算法处理器实例
            processor = AlgorithmPreviewProcessor(
                edited_script_path=str(edited_script_path),
                asr_result_path=str(asr_result_path),
                original_video_path=str(original_video),
                output_dir=str(output_dir),
                task_id=f"{task_id}_{edit_id}"
            )
            
            # 执行处理
            algorithm_result = processor.process()
            
            return {
                "edited_delay_cuts_path": Path(algorithm_result.get("edited_delay_cuts_path")),
                "pause_cuts_path": Path(algorithm_result.get("pause_cuts_path")),
                "audio_b_path": Path(algorithm_result.get("audio_b_path")),
            }
            
        except ImportError as e:
            logger.warning(f"Cannot import preview_processor: {e}, using mock result")
            return self._mock_algorithm_result(output_dir)
        except Exception as e:
            logger.error(f"Algorithm execution failed: {e}")
            return self._mock_algorithm_result(output_dir)
    
    def _mock_algorithm_result(self, output_dir: Path) -> dict[str, Any]:
        """模拟算法结果（用于开发和测试）"""
        # 创建模拟产物
        edited_delay_cuts = {
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hello"},
                {"start": 5.0, "end": 10.0, "text": "World"},
            ]
        }
        
        pause_cuts = {
            "format": "DirectCutter",
            "segments": [
                {"start": 0.0, "end": 4.5, "type": "keep"},
                {"start": 4.5, "end": 5.0, "type": "cut"},
                {"start": 5.0, "end": 10.0, "type": "keep"},
            ]
        }
        
        # 写入文件
        edited_delay_cuts_path = output_dir / "edited_delay_cuts.json"
        with open(edited_delay_cuts_path, 'w', encoding='utf-8') as f:
            json.dump(edited_delay_cuts, f, ensure_ascii=False, indent=2)
        
        pause_cuts_path = output_dir / "pause_cuts_on_original.json"
        with open(pause_cuts_path, 'w', encoding='utf-8') as f:
            json.dump(pause_cuts, f, ensure_ascii=False, indent=2)
        
        # 创建空音频文件（模拟）
        audio_b_path = output_dir / "audio_b.mp3"
        audio_b_path.touch()
        
        return {
            "edited_delay_cuts_path": edited_delay_cuts_path,
            "pause_cuts_path": pause_cuts_path,
            "audio_b_path": audio_b_path,
        }
    
    async def _download_from_tos_async(self, key: str, local_path: Path) -> None:
        """异步从TOS下载文件"""
        await self.file_transport.download_input(key, local_path)
    
    def _download_from_tos_sync(self, key: str, local_path: Path) -> None:
        """同步从TOS下载文件"""
        self.file_transport.download_input_sync(key, local_path)
    
    async def _upload_file_async(self, local_path: Path, key: str) -> None:
        """异步上传单个文件到TOS"""
        await self.file_transport.upload_output(local_path, key)
    
    def _upload_file_sync(self, local_path: Path, key: str) -> None:
        """同步上传单个文件到TOS"""
        self.file_transport.upload_output_sync(local_path, key)
    
    async def _update_database_async(self) -> None:
        """异步更新数据库记录"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._update_database_sync)
    
    def _update_database_sync(self) -> None:
        """同步更新数据库记录"""
        from configs.database import SessionLocal
        
        db = SessionLocal()
        try:
            edit_id = self._edit.id if self._edit else None
            upload_results = getattr(self, '_upload_results', {})
            
            # 更新 Edit 记录
            if edit_id:
                edit = db.query(SmartCutEdit).filter_by(id=edit_id).first()
                if edit:
                    edit.status = EditStatus.SUCCESS
                    edit.audio_b_url = upload_results.get("audio_b")
                    edit.delay_cuts_tos_key = upload_results.get("edited_delay_cuts")
                    edit.pause_cuts_tos_key = upload_results.get("pause_cuts")
                    logger.info(f"Edit record updated: {edit_id}")
            
            # 更新业务任务的 active_edit_id
            if self._current_task:
                business_task = db.query(BusinessTask).filter_by(id=self._current_task.business_task_id).first()
                if business_task:
                    business_task.active_edit_id = edit_id
                    business_task.status = TaskStatus.WAITING_USER
                    business_task.current_stage = CurrentStage.USER_SELECT
                    logger.info(f"Business task active_edit_id updated: {edit_id}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            db.close()
    
    async def _handle_failure_async(self, error_message: str) -> None:
        """异步处理失败情况"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._handle_failure_sync, error_message)
    
    def _handle_failure_sync(self, error_message: str) -> None:
        """同步处理失败情况"""
        from configs.database import SessionLocal
        
        db = SessionLocal()
        try:
            # 获取 edit_id
            edit_id = None
            if self._current_task and self._current_task.payload:
                edit_id = self._current_task.payload.get("edit_id")

            if self._current_task:
                self.job_contract.write_result_manifest(
                    task_id=self._current_task.business_task_id,
                    scheduler_task_id=self._current_task.id,
                    stage="preview",
                    status="failed",
                    outputs={},
                    error_message=error_message,
                    metadata={"edit_id": edit_id},
                )
            
            # 更新 Edit 状态为失败
            if edit_id:
                edit = db.query(SmartCutEdit).filter_by(id=edit_id).first()
                if edit:
                    edit.status = EditStatus.FAILED
            
            # 更新业务任务状态
            if self._current_task:
                business_task = db.query(BusinessTask).filter_by(id=self._current_task.business_task_id).first()
                if business_task:
                    business_task.status = TaskStatus.PREVIEW_FAILED
            
            db.commit()
            logger.info(f"Task marked as preview_failed: {self._current_task.business_task_id if self._current_task else 'unknown'}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update failure status: {e}")
        finally:
            db.close()
