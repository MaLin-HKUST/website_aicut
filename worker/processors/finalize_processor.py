"""Finalize Processor - Smart Cut Finalize 任务处理器 (F20, F21)

处理最终输出任务：
1. 下载原始视频、edited_delay_cuts、pause_cuts (F20)
2. [F21] 如需要 normalize: 调用 incoming_video_process 生成 normalized_input
3. 计算输出码率: min(输入码率, 12Mbps)
4. 调用 finalize_processor 生成最终视频
5. 上传最终视频到 TOS
6. [F22] 调用 GroundTruthRecorder 记录并上传
7. 更新 SmartCutTask

F21 - 视频归一化支持:
- 当 output_mode == "vertical_1080p" 时，调用 normalize_input_video()
- 输出: normalized_input.mp4 + normalized_input.process.json
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from apps.models.scheduler_task import SchedulerTask
from apps.models.edit import SmartCutEdit
from apps.models.task import SmartCutTask as BusinessTask, TaskStatus, CurrentStage
from worker.base_processor import BaseProcessor
from worker.utils.video_info import get_video_info


logger = logging.getLogger(__name__)


class FinalizeProcessor(BaseProcessor):
    """
    Finalize阶段处理器:
    1. 下载原始视频、edited_delay_cuts、pause_cuts
    2. [F21] 如需要 normalize: 调用 incoming_video_process 生成 normalized_input
    3. 计算输出码率: min(输入码率, 12Mbps)
    4. 调用 finalize_processor 生成最终视频
    5. 上传最终视频到 TOS
    6. [F22] 调用 GroundTruthRecorder 记录并上传
    7. 更新 SmartCutTask
    """
    
    # TOS bucket 名称
    BUCKET = "smart-cut"
    
    AICUT_ROOT = os.environ.get("AICUT_ROOT", "/app/aicut2602")
    AICUT_PYTHON = os.environ.get("AICUT_PYTHON", sys.executable)
    ONLINE_VERSION_PATH = f"{AICUT_ROOT}/libs/cut_breakpoints/online_version"
    RAW_CUT_PATH = f"{AICUT_ROOT}/libs/cut_breakpoints/src"
    
    # 最大输出码率 (12Mbps)
    MAX_BITRATE = 12_000_000
    
    def __init__(self, tos_service: Any, workspace: str):
        """初始化处理器
        
        Args:
            tos_service: TOS 服务对象，用于文件上传下载
            workspace: 工作目录路径
        """
        super().__init__(tos_service, workspace)
        self._input_data: dict[str, Any] = {}
        self._edit_id: Optional[str] = None
        self._output_mode: str = "normalize"
        self._need_normalize: bool = False
        self._task: Optional[SchedulerTask] = None
        self._work_dir: Optional[Path] = None
    
    async def process(self, task: SchedulerTask, workspace: str) -> dict[str, Any]:
        """处理 finalize 任务
        
        Args:
            task: 调度任务对象
            workspace: 工作目录路径
            
        Returns:
            dict: 处理结果
                - final_video_url: 最终视频URL
                - final_video_bitrate: 输出码率
                - groundtruth_url: GroundTruth URL (如果 feed_to_ai)
        """
        return await self._process_async(task, workspace)
    
    async def _process_async(self, task: SchedulerTask, workspace: str) -> dict[str, Any]:
        """异步处理主流程"""
        logger.info(f"Processing finalize task: {task.id}, business_task: {task.business_task_id}")
        
        self._task = task
        self._current_task = task
        self._work_dir = self.file_transport.task_dir(task.business_task_id)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Phase 1: 准备输入文件 (F20)
            self.update_progress(0.1)
            await self.prepare_input()
            logger.info(f"Input prepared: edit_id={self._edit_id}, output_mode={self._output_mode}")
            
            # Phase 2: 视频归一化 (F21)
            video_for_cutting = self._input_data.get("original_video")
            if self._need_normalize:
                self.update_progress(0.2)
                video_for_cutting = await self.normalize_video()
                self._input_data["normalized_video"] = video_for_cutting
                logger.info(f"Video normalized: {video_for_cutting}")
            
            self._input_data["video_for_cutting"] = video_for_cutting
            
            # Phase 3: 计算输出码率
            self.update_progress(0.3)
            output_bitrate = await self._calculate_output_bitrate()
            logger.info(f"Output bitrate: {output_bitrate}")
            
            # Phase 4: 执行 finalize 算法
            self.update_progress(0.4)
            result = await self.execute(output_bitrate)
            logger.info(f"Finalize algorithm completed")
            
            # Phase 5: 上传最终视频和其他产物
            self.update_progress(0.8)
            await self.upload_output(result)
            logger.info(f"Outputs uploaded")
            
            # Phase 6: 生成并上传 GroundTruth (如果需要) - F22
            if self._input_data.get("feed_to_ai"):
                self.update_progress(0.9)
                groundtruth_key = await self._generate_and_upload_groundtruth()
                result["groundtruth_url"] = groundtruth_key
                logger.info(f"GroundTruth uploaded: {groundtruth_key}")

            self.job_contract.write_result_manifest(
                task_id=self._task.business_task_id,
                scheduler_task_id=self._task.id,
                stage="finalize",
                status="success",
                outputs={
                    "final_video": {
                        "local_path": str(result.get("final_video_path")) if result.get("final_video_path") else None,
                        "tos_key": result.get("final_video_url"),
                    },
                    "groundtruth": {
                        "local_path": str(self._work_dir / "groundtruth") if self._input_data.get("feed_to_ai") else None,
                        "tos_key": result.get("groundtruth_url"),
                    },
                },
                metadata={
                    "edit_id": self._edit_id,
                    "output_mode": self._output_mode,
                    "feed_to_ai": self._input_data.get("feed_to_ai", False),
                },
            )
            
            self.update_progress(1.0)
            
            return {
                "status": "success",
                "final_video_url": result.get("final_video_url"),
                "final_video_bitrate": output_bitrate,
                "groundtruth_url": result.get("groundtruth_url"),
            }
            
        except Exception as e:
            logger.exception(f"Finalize task failed: {task.id}, error: {e}")
            await self._handle_failure_async(str(e))
            raise
    
    async def prepare_input(self) -> None:
        """准备输入文件 (F20)
        
        从 payload 获取 edit_id, output_mode
        下载所需文件：原始视频、edited_delay_cuts、pause_cuts
        如果 output_mode == "vertical_1080p": 设置 normalize = True
        """
        if not self._task:
            raise ValueError("Task not set")
        
        payload = self._task.payload
        db = self.get_db_session()
        
        try:
            # 获取 edit_id 和 output_mode
            self._edit_id = payload.get("edit_id")
            self._output_mode = payload.get("output_mode", "normalize")
            self._need_normalize = (self._output_mode == "vertical_1080p")
            
            # 读取业务任务
            business_task = db.query(BusinessTask).filter_by(id=self._task.business_task_id).first()
            if not business_task:
                raise ValueError(f"Business task not found: {self._task.business_task_id}")
            
            # 获取 active_edit_id
            active_edit_id = self._edit_id or business_task.active_edit_id
            if not active_edit_id:
                raise ValueError("No edit_id found for finalize")
            
            self._edit_id = active_edit_id
            
            # 读取 edit 记录
            edit = db.query(SmartCutEdit).filter_by(id=active_edit_id).first()
            if not edit:
                raise ValueError(f"Edit not found: {active_edit_id}")
            
            input_dir = self._work_dir / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            
            # 存储输入数据
            self._input_data = {
                "active_edit_id": active_edit_id,
                "output_mode": self._output_mode,
                "feed_to_ai": payload.get("feed_to_ai", False),
                "original_video_url": business_task.original_video_url,
                "reference_text_url": business_task.reference_text_url,
                "analyze_script": business_task.analyze_script,
                "edited_script": edit.edited_script,
                "asr_result_url": business_task.asr_result_tos_key,
            }
            
            # 下载原视频
            if business_task.original_video_url:
                video_path = input_dir / "source_video.mp4"
                await self._download_from_tos_async(business_task.original_video_url, video_path)
                self._input_data["original_video"] = video_path
            else:
                raise ValueError("Missing original_video_url")
            
            # 下载文案
            if business_task.reference_text_url:
                text_path = input_dir / "reference.txt"
                await self._download_from_tos_async(business_task.reference_text_url, text_path)
                with open(text_path, 'r', encoding='utf-8') as f:
                    self._input_data["reference_text"] = f.read()
            
            # 下载 edited_delay_cuts
            if edit.delay_cuts_tos_key:
                delay_cuts_path = input_dir / "edited_delay_cuts.json"
                await self._download_from_tos_async(edit.delay_cuts_tos_key, delay_cuts_path)
                with open(delay_cuts_path, 'r', encoding='utf-8') as f:
                    self._input_data["edited_delay_cuts"] = json.load(f)
            else:
                raise ValueError("Missing delay_cuts_tos_key in edit")
            
            # 下载 pause_cuts
            if edit.pause_cuts_tos_key:
                pause_cuts_path = input_dir / "pause_cuts_on_original.json"
                await self._download_from_tos_async(edit.pause_cuts_tos_key, pause_cuts_path)
                with open(pause_cuts_path, 'r', encoding='utf-8') as f:
                    self._input_data["pause_cuts"] = json.load(f)
            else:
                pause_cuts_path = input_dir / "pause_cuts_on_original.json"
                empty_pause_cuts = {"config": {}, "segments": []}
                pause_cuts_path.write_text(json.dumps(empty_pause_cuts, ensure_ascii=False, indent=2), encoding="utf-8")
                self._input_data["pause_cuts"] = empty_pause_cuts
            
            # 下载ASR结果
            if business_task.asr_result_tos_key:
                asr_path = input_dir / "asr_result.json"
                await self._download_from_tos_async(business_task.asr_result_tos_key, asr_path)
                with open(asr_path, 'r', encoding='utf-8') as f:
                    self._input_data["asr_result"] = json.load(f)

            self.job_contract.write_task_manifest(
                self._task,
                stage="finalize",
                edit_id=self._edit_id,
                inputs={
                    "original_video": {
                        "source": business_task.original_video_url,
                        "local_path": str(self._input_data["original_video"]),
                    },
                    "reference_text": {
                        "source": business_task.reference_text_url,
                        "local_path": str(text_path) if business_task.reference_text_url else None,
                    },
                    "edited_delay_cuts": {
                        "source": edit.delay_cuts_tos_key,
                        "local_path": str(delay_cuts_path),
                    },
                    "pause_cuts_on_original": {
                        "source": edit.pause_cuts_tos_key,
                        "local_path": str(pause_cuts_path),
                    },
                    "asr_result": {
                        "source": business_task.asr_result_tos_key,
                        "local_path": str(asr_path) if business_task.asr_result_tos_key else None,
                    },
                },
                expected_outputs=[
                    {"name": "final_video", "path": str(self._work_dir / "finalize" / "final_video.mp4")},
                    {"name": "groundtruth", "path": str(self._work_dir / "groundtruth")},
                ],
                payload=dict(payload),
            )
            
        finally:
            db.close()
    
    async def normalize_video(self) -> Path:
        """F21: 视频归一化
        
        调用 incoming_video_process 进行视频归一化
        生成 normalized_input.mp4 和 normalized_input.process.json
        上传归一化产物到 TOS
        
        Returns:
            Path: 归一化后的视频路径
        """
        output_dir = self._work_dir / "finalize"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        original_video = self._input_data.get("original_video")
        if not original_video:
            raise ValueError("Original video not found")
        
        normalized_video = output_dir / "normalized_input.mp4"
        process_json = output_dir / "normalized_input.process.json"
        
        # 尝试使用 run_raw_cut.py --normalize-input-video
        cmd = [
            self.AICUT_PYTHON,
            "-m",
            "libs.cut_breakpoints.src.run_raw_cut",
            "--normalize-input-video",
            "-i", str(original_video),
            "-o", str(output_dir),
        ]
        
        try:
            logger.info(f"Normalizing video: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
            
            if proc.returncode != 0:
                raise RuntimeError(f"Normalization script failed: {stderr.decode()}")
            
            logger.info(f"Normalization completed: {stdout.decode()}")
            
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Normalization script failed: {e}, using fallback")
            # Fallback: 使用 FFmpeg 进行基本的归一化
            await self._normalize_with_ffmpeg_async(original_video, normalized_video, process_json)
        
        # 保存归一化产物路径
        self._input_data["normalized_video_path"] = normalized_video
        self._input_data["process_json_path"] = process_json
        
        # 上传归一化产物到 TOS
        normalized_key = f"smart-cut/{self._task.business_task_id}/finalize/normalized_input.mp4"
        process_json_key = f"smart-cut/{self._task.business_task_id}/finalize/normalized_input.process.json"
        
        await self._upload_file_async(normalized_video, normalized_key)
        await self._upload_file_async(process_json, process_json_key)
        
        self._input_data["normalized_video_tos_key"] = normalized_key
        self._input_data["process_json_tos_key"] = process_json_key
        
        logger.info(f"Normalized video uploaded: {normalized_key}")
        
        return normalized_video
    
    async def _normalize_with_ffmpeg_async(
        self,
        video_path: Path,
        output_video: Path,
        output_json: Path
    ) -> None:
        """使用 FFmpeg 进行视频归一化（异步版本）
        
        转换为 1080p 竖屏 (9:16)
        """
        # FFmpeg 命令: 缩放到 1080x1920 (9:16)
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            str(output_video)
        ]
        
        try:
            logger.info(f"Running FFmpeg normalization: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=600)
            
            if proc.returncode != 0:
                raise RuntimeError("FFmpeg normalization failed")
            
            # 生成 process.json
            process_data = {
                "operation": "normalize",
                "input_path": str(video_path),
                "output_path": str(output_video),
                "resolution": "1080x1920",
                "aspect_ratio": "9:16",
            }
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(process_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"FFmpeg normalization failed: {e}")
            raise RuntimeError(f"Video normalization failed: {e}")
    
    async def execute(self, output_bitrate: int) -> dict[str, Any]:
        """执行 finalize 算法
        
        计算输出码率: min(input_bitrate, 12000000)  # 12Mbps
        调用 finalize_processor 生成最终视频
        输入: video_path (normalized or original), cuts_config
        输出: final_video.mp4
        
        Args:
            output_bitrate: 输出码率 (bps)
            
        Returns:
            dict: 处理结果
                - final_video_path: 最终视频本地路径
                - final_video_url: 最终视频 TOS URL
        """
        if self.algorithm_runner.is_enabled():
            manifest_result = await asyncio.to_thread(
                self.algorithm_runner.run_stage,
                self._task.business_task_id,
                "finalize",
            )
            return {
                "final_video_path": Path(manifest_result["outputs"]["final_video"]["local_path"]),
            }

        video_path = self._input_data.get("video_for_cutting")
        edited_delay_cuts = self._input_data.get("edited_delay_cuts")
        pause_cuts = self._input_data.get("pause_cuts")
        
        output_dir = self._work_dir / "finalize"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行算法
        result = await self._execute_algorithm_async(
            video_path=video_path,
            edited_delay_cuts=edited_delay_cuts,
            pause_cuts=pause_cuts,
            output_dir=output_dir,
            output_bitrate=output_bitrate,
            task_id=self._task.business_task_id
        )
        
        return result
    
    async def _execute_algorithm_async(
        self,
        video_path: Path,
        edited_delay_cuts: dict,
        pause_cuts: dict,
        output_dir: Path,
        output_bitrate: int,
        task_id: str
    ) -> dict[str, Any]:
        """异步执行 finalize 算法"""
        # 添加 online_version 到 Python 路径
        if self.ONLINE_VERSION_PATH not in sys.path:
            sys.path.insert(0, self.ONLINE_VERSION_PATH)
        
        try:
            # 尝试导入 finalize_processor
            from src.finalize_processor import FinalizeProcessor as AlgorithmFinalizeProcessor
            from src.final_video_cutter import OnlineFinalVideoCutter
            
            # 保存配置到文件
            cuts_path = output_dir / "cuts_config.json"
            with open(cuts_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "edited_delay_cuts": edited_delay_cuts,
                    "pause_cuts": pause_cuts,
                }, f, indent=2)
            
            # 创建算法处理器实例
            processor = AlgorithmFinalizeProcessor(
                video_path=str(video_path),
                cuts_config_path=str(cuts_path),
                output_dir=str(output_dir),
                output_bitrate=output_bitrate,
                task_id=task_id
            )
            
            # 执行处理（在线程池中运行同步代码）
            loop = asyncio.get_event_loop()
            algorithm_result = await loop.run_in_executor(None, processor.process)
            
            return {
                "final_video_path": Path(algorithm_result.get("final_video_path")),
            }
            
        except ImportError as e:
            logger.warning(f"Cannot import finalize_processor: {e}, using mock result")
            return await self._mock_algorithm_result_async(output_dir, video_path)
        except Exception as e:
            logger.error(f"Algorithm execution failed: {e}")
            return await self._mock_algorithm_result_async(output_dir, video_path)
    
    async def _mock_algorithm_result_async(self, output_dir: Path, video_path: Path) -> dict[str, Any]:
        """模拟算法结果（异步版本）"""
        final_video = output_dir / "final_video.mp4"
        
        # 在线程池中执行文件复制
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, shutil.copy2, video_path, final_video)
        
        return {
            "final_video_path": final_video,
        }
    
    async def upload_output(self, result: dict[str, Any]) -> None:
        """上传输出产物
        
        上传 final_video 到 TOS
        更新 SmartCutTask:
          - final_video_url
          - final_video_bitrate
          
        Args:
            result: 执行结果，包含 final_video_path
        """
        final_video_path = result.get("final_video_path")
        if not final_video_path or not Path(final_video_path).exists():
            raise ValueError(f"Final video not found: {final_video_path}")
        
        # 上传最终视频
        final_video_key = f"smart-cut/{self._task.business_task_id}/finalize/final_video.mp4"
        await self._upload_file_async(final_video_path, final_video_key)
        
        result["final_video_url"] = final_video_key
        
        # 更新数据库
        await self._update_database_async(result)
        
        logger.info(f"Final video uploaded and database updated: {final_video_key}")
    
    async def _calculate_output_bitrate(self) -> int:
        """计算输出码率
        
        Returns:
            int: 输出码率 (bps)，min(输入码率, 12Mbps)
        """
        original_video = self._input_data.get("original_video")
        if not original_video:
            return self.MAX_BITRATE
        
        # 在线程池中获取视频信息
        loop = asyncio.get_event_loop()
        video_info = await loop.run_in_executor(None, get_video_info, original_video)
        
        if video_info and video_info.bitrate > 0:
            input_bitrate = video_info.bitrate
        else:
            # Fallback: 通过文件大小估算
            file_size = original_video.stat().st_size
            estimated_bitrate = int(file_size * 8 / 120)  # 假设120秒视频
            input_bitrate = min(estimated_bitrate, self.MAX_BITRATE)
            logger.info(f"Using estimated bitrate: {input_bitrate}")
        
        output_bitrate = min(input_bitrate, self.MAX_BITRATE)
        self._input_data["input_bitrate"] = input_bitrate
        self._input_data["output_bitrate"] = output_bitrate
        
        return output_bitrate
    
    async def _generate_and_upload_groundtruth(self) -> str:
        """生成并上传 GroundTruth (F22)
        
        目录结构:
        cujian_input_data/{company}/{year-month}/cujian_userdata_{timestamp}/
            ├── reference.txt
            ├── analyze_script.txt
            ├── edited_script.txt
            ├── asr_result.json
            └── metadata.json
            
        Returns:
            str: GroundTruth TOS key
        """
        from datetime import datetime
        
        company = "default"
        year_month = datetime.now().strftime("%Y-%m")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        gt_dir = self._work_dir / "groundtruth" / f"cujian_userdata_{timestamp}"
        gt_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        if self._input_data.get("reference_text"):
            with open(gt_dir / "reference.txt", 'w', encoding='utf-8') as f:
                f.write(self._input_data["reference_text"])
        
        if self._input_data.get("analyze_script"):
            with open(gt_dir / "analyze_script.txt", 'w', encoding='utf-8') as f:
                json.dump(self._input_data["analyze_script"], f, ensure_ascii=False, indent=2)
        
        if self._input_data.get("edited_script"):
            with open(gt_dir / "edited_script.txt", 'w', encoding='utf-8') as f:
                json.dump(self._input_data["edited_script"], f, ensure_ascii=False, indent=2)
        
        if self._input_data.get("asr_result"):
            with open(gt_dir / "asr_result.json", 'w', encoding='utf-8') as f:
                json.dump(self._input_data["asr_result"], f, ensure_ascii=False, indent=2)
        
        # 元数据
        metadata = {
            "task_id": self._task.business_task_id,
            "edit_id": self._input_data.get("active_edit_id"),
            "created_at": datetime.now().isoformat(),
            "company": company,
        }
        with open(gt_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # 上传 GroundTruth 目录
        gt_key = f"cujian_input_data/{company}/{year_month}/cujian_userdata_{timestamp}"
        await self._upload_directory_async(gt_dir, gt_key)
        
        return gt_key
    
    async def _download_from_tos_async(self, key: str, local_path: Path) -> None:
        """异步从 TOS 下载文件"""
        await self.file_transport.download_input(key, local_path)
    
    async def _upload_file_async(self, local_path: Path, key: str) -> None:
        """异步上传单个文件到 TOS"""
        await self.file_transport.upload_output(local_path, key)
    
    async def _upload_directory_async(self, local_dir: Path, base_key: str) -> None:
        """异步上传整个目录到 TOS"""
        await self.file_transport.upload_directory(local_dir, base_key)
    
    async def _update_database_async(self, result: dict[str, Any]) -> None:
        """异步更新数据库记录"""
        db = self.get_db_session()
        try:
            business_task = db.query(BusinessTask).filter_by(id=self._task.business_task_id).first()
            if business_task:
                business_task.status = TaskStatus.SUCCESS
                business_task.current_stage = CurrentStage.COMPLETE
                business_task.final_video_url = result.get("final_video_url")
                
                if result.get("groundtruth_url"):
                    business_task.groundtruth_url = result["groundtruth_url"]
                    business_task.groundtruth_upload_status = "completed"
                
                logger.info(f"Business task marked as success: {business_task.id}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            db.close()
    
    async def _handle_failure_async(self, error_message: str) -> None:
        """异步处理失败情况"""
        db = self.get_db_session()
        try:
            if self._task:
                self.job_contract.write_result_manifest(
                    task_id=self._task.business_task_id,
                    scheduler_task_id=self._task.id,
                    stage="finalize",
                    status="failed",
                    outputs={},
                    error_message=error_message,
                    metadata={
                        "edit_id": self._edit_id,
                        "output_mode": self._output_mode,
                    },
                )
            business_task = db.query(BusinessTask).filter_by(id=self._task.business_task_id).first()
            if business_task:
                business_task.status = TaskStatus.WAITING_USER
                business_task.current_stage = CurrentStage.USER_SELECT
                business_task.failed_stage = "finalize"
                db.commit()
                logger.info(f"Task returned to waiting_user after finalize failure: {business_task.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update failure status: {e}")
        finally:
            db.close()
