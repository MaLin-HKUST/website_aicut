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
from apps.services.smart_cut_contract import (
    STATUS_DETAIL_GENERATING_SUBTITLE,
    default_status_detail,
)
from worker.base_processor import BaseProcessor
from worker.services.pause_cuts import generate_pause_cuts_from_delay_audio
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
    # 最大输出码率 (12Mbps by default)
    MAX_BITRATE = int(os.environ.get("SMART_CUT_FINALIZE_MAX_BITRATE", "12000000"))
    REENCODE_BITRATE = int(os.environ.get("SMART_CUT_FINALIZE_REENCODE_BITRATE", "0"))
    
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
                    "subtitle_srt": {
                        "local_path": str(result.get("subtitle_srt_path")) if result.get("subtitle_srt_path") else None,
                        "tos_key": result.get("subtitle_srt_url"),
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
                "subtitle_srt_url": result.get("subtitle_srt_url"),
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
            
            # 下载或生成 pause_cuts。PauseCut 是 DelayCut 后的必备产物，
            # finalize 不允许用空文件替代。
            pause_cuts_source = edit.pause_cuts_tos_key or payload.get("pause_cuts_on_original_tos_key")
            if pause_cuts_source:
                pause_cuts_path = input_dir / "pause_cuts_on_original.json"
                await self._download_from_tos_async(pause_cuts_source, pause_cuts_path)
                if not edit.pause_cuts_tos_key:
                    edit.pause_cuts_tos_key = pause_cuts_source
                    db.commit()
                with open(pause_cuts_path, 'r', encoding='utf-8') as f:
                    self._input_data["pause_cuts"] = json.load(f)
            else:
                pause_cuts_path = input_dir / "pause_cuts_on_original.json"
                try:
                    await self._generate_and_persist_pause_cuts_for_edit(
                        db=db,
                        business_task=business_task,
                        edit=edit,
                        input_dir=input_dir,
                        pause_cuts_path=pause_cuts_path,
                    )
                except Exception as exc:
                    logger.warning(
                        "Pause cuts unavailable for edit %s (%s); proceeding without --pause-cuts",
                        edit.id,
                        exc,
                    )
                if pause_cuts_path.exists():
                    with open(pause_cuts_path, 'r', encoding='utf-8') as f:
                        self._input_data["pause_cuts"] = json.load(f)
                else:
                    self._input_data["pause_cuts"] = {}
            
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
                    {"name": "subtitle_srt", "path": str(self._work_dir / "finalize" / "subtitle" / "final_video.srt")},
                    {"name": "groundtruth", "path": str(self._work_dir / "groundtruth")},
                ],
                payload=dict(payload),
            )
            
        finally:
            db.close()

    async def _generate_and_persist_pause_cuts_for_edit(
        self,
        *,
        db: Any,
        business_task: BusinessTask,
        edit: SmartCutEdit,
        input_dir: Path,
        pause_cuts_path: Path,
    ) -> None:
        """Generate missing mandatory PauseCut output and store it on the edit."""
        delay_cuts_path = input_dir / "edited_delay_cuts.json"
        original_video_path = input_dir / "source_video.mp4"
        audio_source = edit.audio_b_url or edit.audio_a_url
        if not audio_source:
            raise RuntimeError(
                f"Cannot generate required pause cuts for edit {edit.id}: missing post-DelayCut audio"
            )

        post_delay_audio_path = input_dir / "post_delay_audio.mp3"
        await self._download_from_tos_async(audio_source, post_delay_audio_path)
        generate_pause_cuts_from_delay_audio(
            original_video=original_video_path,
            edited_delay_cuts_path=delay_cuts_path,
            audio_path=post_delay_audio_path,
            pause_cuts_path=pause_cuts_path,
            aicut_root=self.AICUT_ROOT,
            source="smart_cut_finalize_repair",
        )

        pause_cuts_key = f"smart-cut/{business_task.id}/preview/{edit.id}/pause_cuts_on_original.json"
        await self._upload_file_async(pause_cuts_path, pause_cuts_key)
        edit.pause_cuts_tos_key = pause_cuts_key
        db.commit()
        logger.info(
            "Generated required pause cuts for finalize: task_id=%s edit_id=%s key=%s",
            business_task.id,
            edit.id,
            pause_cuts_key,
        )
    
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
        try:
            return await self._run_formal_flow_b_async(
                video_path=video_path,
                output_dir=output_dir,
                output_bitrate=output_bitrate,
            )
        except Exception as e:
            logger.exception("Formal finalize flow-b failed; refusing to publish fallback black/mock output")
            raise

    async def _run_formal_flow_b_async(
        self,
        video_path: Path,
        output_dir: Path,
        output_bitrate: int | None = None,
    ) -> dict[str, Any]:
        input_dir = self._work_dir / "input"
        delay_cuts_path = input_dir / "edited_delay_cuts.json"
        asr_result_path = input_dir / "asr_result.json"
        pause_cuts_path = input_dir / "pause_cuts_on_original.json"

        if not delay_cuts_path.exists():
            raise ValueError(f"Missing delay cuts file for formal finalize: {delay_cuts_path}")
        if not asr_result_path.exists():
            raise ValueError(f"Missing ASR result file for formal finalize: {asr_result_path}")

        base_name = f"task_{self._task.business_task_id}_formal_finalize"
        cmd = [
            self.AICUT_PYTHON,
            "-m",
            "libs.cut_breakpoints.src.run_raw_cut",
            "-i",
            str(video_path),
            "-o",
            str(output_dir),
            "--flow-b",
            "--delay-cuts",
            str(delay_cuts_path),
            "--asr-result",
            str(asr_result_path),
            "-n",
            base_name,
        ]
        if pause_cuts_path.exists():
            cmd.extend(["--pause-cuts", str(pause_cuts_path)])
        if self._output_mode == "original":
            fallback_mbps = max((output_bitrate or self.MAX_BITRATE) / 1_000_000, 0.001)
            cmd.extend(
                [
                    "--bitrate-mode",
                    "min_of_input_and_cap",
                    "--video-bitrate-fallback-mbps",
                    f"{fallback_mbps:.6f}",
                ]
            )

        logger.info("Running formal finalize flow-b: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.AICUT_ROOT,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode() or stdout.decode() or "run_raw_cut flow-b failed")

        final_video_candidates = [
            output_dir / f"{base_name}_final.mp4",
            output_dir / f"{video_path.stem}_final.mp4",
            output_dir / "final_video.mp4",
        ]
        final_video_path = next((path for path in final_video_candidates if path.exists()), None)
        if final_video_path is None:
            generated = sorted(output_dir.glob("*_final.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
            final_video_path = generated[0] if generated else None
        if final_video_path is None or not final_video_path.exists():
            raise RuntimeError(f"Formal finalize did not produce an output video. stdout={stdout.decode()}")

        canonical_final_video = output_dir / "final_video.mp4"
        if final_video_path != canonical_final_video:
            shutil.copy2(final_video_path, canonical_final_video)
            final_video_path = canonical_final_video

        final_video_path = await self._maybe_reencode_final_video(final_video_path)

        return {
            "final_video_path": final_video_path,
        }

    async def _maybe_reencode_final_video(self, final_video_path: Path) -> Path:
        """Optionally shrink the final artifact for constrained upload links."""
        if self._output_mode == "original":
            logger.info("Skipping final video re-encode for original output mode: %s", final_video_path)
            return final_video_path

        if self.REENCODE_BITRATE <= 0:
            return final_video_path

        compressed_path = final_video_path.with_name(f"{final_video_path.stem}.compressed.mp4")
        bitrate = str(self.REENCODE_BITRATE)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(final_video_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            bitrate,
            "-maxrate",
            bitrate,
            "-bufsize",
            str(self.REENCODE_BITRATE * 2),
            "-c:a",
            "aac",
            "-b:a",
            os.environ.get("SMART_CUT_FINALIZE_REENCODE_AUDIO_BITRATE", "96k"),
            "-movflags",
            "+faststart",
            str(compressed_path),
        ]
        logger.info("Re-encoding final video for upload: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=int(os.environ.get("SMART_CUT_FINALIZE_REENCODE_TIMEOUT_SECONDS", "1800")),
        )
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode() or stdout.decode() or "final video re-encode failed")

        if compressed_path.stat().st_size < final_video_path.stat().st_size:
            shutil.move(str(compressed_path), str(final_video_path))
            logger.info("Final video re-encoded: %s", final_video_path)
        else:
            compressed_path.unlink(missing_ok=True)
            logger.info("Skipped re-encoded video because it was not smaller")
        return final_video_path
    
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

        await self._set_status_detail_async(STATUS_DETAIL_GENERATING_SUBTITLE)
        subtitle_srt_path = await self._generate_subtitle_srt_async(Path(final_video_path))
        subtitle_srt_key = f"smart-cut/{self._task.business_task_id}/finalize/final_video.srt"
        await self._upload_file_async(subtitle_srt_path, subtitle_srt_key)
        result["subtitle_srt_path"] = subtitle_srt_path
        result["subtitle_srt_url"] = subtitle_srt_key
        
        # 更新数据库
        await self._update_database_async(result)
        
        logger.info(f"Final video uploaded and database updated: {final_video_key}")

    async def _set_status_detail_async(self, status_detail: str) -> None:
        db = self.get_db_session()
        try:
            business_task = db.query(BusinessTask).filter_by(id=self._task.business_task_id).first()
            if business_task:
                business_task.status_detail = status_detail
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _subtitle_config(self) -> dict[str, str | int | float]:
        return {
            "model": os.getenv("SMART_CUT_SUBTITLE_MODEL", "deepseek-v4-flash"),
            "temperature": float(os.getenv("SMART_CUT_SUBTITLE_TEMPERATURE", "0.3")),
            "reasoning_effort": os.getenv("SMART_CUT_SUBTITLE_REASONING_EFFORT", "disabled"),
            "max_tokens": int(os.getenv("SMART_CUT_SUBTITLE_MAX_TOKENS", "8192")),
            "max_caption_chars": int(os.getenv("SMART_CUT_SUBTITLE_MAX_CAPTION_CHARS", "11")),
            "timeout_seconds": int(os.getenv("SMART_CUT_SUBTITLE_TIMEOUT_SECONDS", "1800")),
        }

    def _subtitle_script_path(self) -> Path:
        return Path(os.environ.get("AICUT_ROOT", self.AICUT_ROOT)) / "scripts" / "smart_cut" / "run_deepseek_semantic_srt.sh"

    def _script_value_to_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for segment in value:
                if isinstance(segment, str):
                    parts.append(segment)
                elif isinstance(segment, dict):
                    parts.append(str(segment.get("text", "")))
                else:
                    parts.append(str(segment))
            return "".join(parts)
        if isinstance(value, dict) and isinstance(value.get("segments"), list):
            parts: list[str] = []
            for segment in value["segments"]:
                if isinstance(segment, str):
                    parts.append(segment)
                elif isinstance(segment, dict):
                    parts.append(str(segment.get("text", "")))
                else:
                    parts.append(str(segment))
            return "".join(parts)
        try:
            return json.dumps(value, ensure_ascii=False, indent=2)
        except TypeError:
            return str(value)

    def _write_subtitle_script_input(self, subtitle_output_dir: Path) -> Path:
        script_text = self._script_value_to_text(self._input_data.get("edited_script")).strip()
        script_source = "edited_script"
        if not script_text:
            script_text = self._script_value_to_text(self._input_data.get("analyze_script")).strip()
            script_source = "analyze_script"
        if not script_text:
            raise ValueError("Missing edited_script/analyze_script for semantic subtitle generation")

        script_path = subtitle_output_dir / "final_video_Script1.txt"
        script_path.write_text(script_text + "\n", encoding="utf-8")
        logger.info("Prepared semantic subtitle script from %s: %s", script_source, script_path)
        return script_path

    async def _generate_subtitle_srt_async(self, final_video_path: Path) -> Path:
        subtitle_script_path = self._subtitle_script_path()
        if not subtitle_script_path.exists():
            raise ValueError(f"Subtitle script not found: {subtitle_script_path}")

        subtitle_output_dir = self._work_dir / "finalize" / "subtitles"
        subtitle_output_dir.mkdir(parents=True, exist_ok=True)
        semantic_script_input = self._write_subtitle_script_input(subtitle_output_dir)
        config = self._subtitle_config()
        expected_srt = subtitle_output_dir / "final_video_checked.srt"
        cmd = [
            "bash",
            str(subtitle_script_path),
            "--video",
            str(final_video_path),
            "--script",
            str(semantic_script_input),
            "--max-caption-chars",
            str(config["max_caption_chars"]),
            "--output-dir",
            str(subtitle_output_dir),
            "--name",
            "final_video",
        ]

        logger.info("Generating DeepSeek semantic subtitle SRT: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.AICUT_ROOT,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=int(config["timeout_seconds"]))
        if proc.returncode != 0:
            raise RuntimeError(f"Semantic subtitle generation failed: {stderr.decode() or stdout.decode()}")
        if not expected_srt.exists():
            raise RuntimeError(f"Semantic subtitle generation did not create checked SRT: {expected_srt}")
        return expected_srt
    
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
                business_task.status_detail = default_status_detail(TaskStatus.SUCCESS.value)
                business_task.final_video_url = result.get("final_video_url")
                business_task.subtitle_srt_url = result.get("subtitle_srt_url")
                
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
                business_task.status = TaskStatus.FINALIZE_FAILED
                business_task.current_stage = CurrentStage.FINALIZE
                business_task.failed_stage = "finalize"
                business_task.status_detail = default_status_detail(TaskStatus.FINALIZE_FAILED.value)
                db.commit()
                logger.info(f"Task marked finalize_failed after finalize failure: {business_task.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update failure status: {e}")
        finally:
            db.close()
