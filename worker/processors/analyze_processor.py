"""Analyze Processor - Smart Cut Analyze 任务处理器 (F16)

处理视频分析任务：
1. 下载输入视频和文案到 work_dir/input/
2. 调用 run_raw_cut.py --flow-a 执行ASR和脚本生成
3. 解析产物 (script, asr, delay_cuts, audio_a)
4. 上传产物到 TOS (key: smart-cut/{task_id}/analyze/{filename})
5. 更新 SmartCutTask 和 SmartCutEdit 数据库记录
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from apps.models.scheduler_task import SchedulerTask
from apps.models.edit import SmartCutEdit, EditStatus
from apps.models.task import SmartCutTask as BusinessTask, TaskStatus, CurrentStage
from worker.processors.base_stage_processor import BaseStageProcessor


logger = logging.getLogger(__name__)


class AnalyzeProcessor(BaseStageProcessor):
    """Smart Cut Analyze 阶段处理器
    
    执行视频分析，生成口播脚本和ASR结果。
    调用算法: python /app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py
    
    产物文件:
    - {prefix}_Script1.txt -> script
    - {prefix}_ASR.Result.json -> asr_result
    - {prefix}_DelayCutSegments.json -> delay_cuts
    - {prefix}_audio_a.mp3 -> audio_a
    """
    
    AICUT_ROOT = os.environ.get("AICUT_ROOT", "/app/aicut2602")
    AICUT_PYTHON = os.environ.get("AICUT_PYTHON", sys.executable)
    ALGORITHM_MODULE = "libs.cut_breakpoints.src.run_raw_cut"
    
    def __init__(self, tos_service: Any, workspace: str):
        """初始化 AnalyzeProcessor
        
        Args:
            tos_service: TOS 服务对象
            workspace: 工作目录路径
        """
        super().__init__(tos_service, workspace)
        self._input_paths: dict[str, Path] = {}
        self._output_dir: Path = Path()
        self._prefix: str = ""
    
    async def prepare_input(self) -> None:
        """准备输入文件
        
        从 scheduler_task.payload 获取 tos_keys，
        使用 tos_service.download_file 下载到 work_dir/input/
        
        Raises:
            ValueError: 缺少 video_key 或 text_key
            RuntimeError: 下载失败
        """
        if not self._current_task:
            raise RuntimeError("No task set")
        
        input_dir = self.file_transport.input_dir(self._task_id)
        input_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = f"task_{self._task_id}"
        
        payload = self._current_task.payload
        
        # 获取视频 key
        video_key = (
            payload.get("original_video_tos_key")
            or payload.get("video_key")
            or payload.get("video_url")
        )
        if not video_key:
            raise ValueError("Missing video_key or video_url in task payload")
        
        # 获取文案 key
        text_key = (
            payload.get("reference_text_tos_key")
            or payload.get("text_key")
            or payload.get("text_url")
        )
        if not text_key:
            raise ValueError("Missing text_key or text_url in task payload")
        
        # 下载视频文件
        video_path = input_dir / "source_video.mp4"
        self._download_from_tos(video_key, video_path)
        self._input_paths["video"] = video_path
        logger.info(f"Video downloaded: {video_key} -> {video_path}")
        
        # 下载文案文件
        text_path = input_dir / "reference.txt"
        self._download_from_tos(text_key, text_path)
        self._input_paths["text"] = text_path
        logger.info(f"Text downloaded: {text_key} -> {text_path}")

        self.job_contract.write_task_manifest(
            self._current_task,
            stage="analyze",
            inputs={
                "original_video": {
                    "source": video_key,
                    "local_path": str(video_path),
                },
                "reference_text": {
                    "source": text_key,
                    "local_path": str(text_path),
                },
            },
            expected_outputs=[
                {"name": "script", "path": str(self._work_dir / "analyze" / "output" / f"{self._prefix}_Script1.txt")},
                {"name": "asr_result", "path": str(self._work_dir / "analyze" / "output" / f"{self._prefix}_ASR.Result.json")},
                {"name": "delay_cuts", "path": str(self._work_dir / "analyze" / "output" / f"{self._prefix}_DelayCutSegments.json")},
                {"name": "audio_a", "path": str(self._work_dir / "analyze" / "output" / f"{self._prefix}_audio_a.mp3")},
            ],
            payload=dict(payload),
        )
    
    async def execute(self) -> dict:
        """执行分析算法
        
        构建命令: python run_raw_cut.py -i {video} -r {text} -o {output_dir} --flow-a -n task_{task_id}
        使用 subprocess.run 执行
        
        解析产物文件:
        - {prefix}_Script1.txt -> script
        - {prefix}_ASR.Result.json -> asr_result
        - {prefix}_DelayCutSegments.json -> delay_cuts
        - {prefix}_audio_a.mp3 -> audio_a
        
        Returns:
            dict: 产物信息
                - script: 解析后的脚本内容 (list[dict])
                - asr_result: ASR 识别结果 (dict)
                - delay_cuts: 延迟切割配置 (dict)
                - audio_a_path: 音频文件路径 (Path)
                - script_path: 脚本文件路径 (Path)
                - asr_path: ASR 结果文件路径 (Path)
                - delay_cuts_path: 延迟切割配置路径 (Path)
                
        Raises:
            RuntimeError: 算法执行失败或超时
        """
        if not self._current_task:
            raise RuntimeError("No task set")

        if self.algorithm_runner.is_enabled():
            self._output_dir = self._work_dir / "analyze" / "output"
            self._output_dir.mkdir(parents=True, exist_ok=True)
            manifest_result = await asyncio.to_thread(
                self.algorithm_runner.run_stage,
                self._task_id,
                "analyze",
            )
            if manifest_result["status"] != "success":
                raise RuntimeError(manifest_result.get("error_message") or "Algorithm container failed")
            return self._parse_outputs()
        
        # 设置输出目录和前缀
        self._output_dir = self._work_dir / "analyze" / "output"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = f"task_{self._task_id}"
        
        # 构建命令
        cmd = [
            self.AICUT_PYTHON,
            "-m",
            self.ALGORITHM_MODULE,
            "-i", str(self._input_paths["video"]),
            "-r", str(self._input_paths["text"]),
            "-o", str(self._output_dir),
            "--flow-a",
            "-n", self._prefix,
        ]
        
        logger.info(f"Running algorithm: {' '.join(cmd)}")
        
        # 执行命令
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1小时超时
                cwd=self.AICUT_ROOT,
            )
            logger.info(f"Algorithm stdout: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Algorithm failed: {e.stderr}")
            raise RuntimeError(f"Algorithm execution failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Algorithm execution timeout (1 hour)")
        
        # 解析产物
        return self._parse_outputs()
    
    def _parse_outputs(self) -> dict[str, Any]:
        """解析算法产物文件
        
        Returns:
            dict: 产物数据
        """
        result = {}
        prefix = self._prefix
        output_dir = self._output_dir
        
        # 解析脚本
        script_path = output_dir / f"{prefix}_Script1.txt"
        if script_path.exists():
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            result["script"] = self._parse_script(script_content)
            result["script_path"] = script_path
            logger.info(f"Script parsed: {script_path}")
        else:
            logger.warning(f"Script file not found: {script_path}")
            result["script"] = None
            result["script_path"] = None
        
        # 解析ASR结果
        asr_path = output_dir / f"{prefix}_ASR.Result.json"
        if asr_path.exists():
            with open(asr_path, 'r', encoding='utf-8') as f:
                result["asr_result"] = json.load(f)
            result["asr_path"] = asr_path
            logger.info(f"ASR result parsed: {asr_path}")
        else:
            logger.warning(f"ASR file not found: {asr_path}")
            result["asr_result"] = None
            result["asr_path"] = None
        
        # 解析延迟切割配置
        delay_cuts_path = output_dir / f"{prefix}_DelayCutSegments.json"
        if delay_cuts_path.exists():
            with open(delay_cuts_path, 'r', encoding='utf-8') as f:
                result["delay_cuts"] = json.load(f)
            result["delay_cuts_path"] = delay_cuts_path
            logger.info(f"Delay cuts parsed: {delay_cuts_path}")
        else:
            logger.warning(f"Delay cuts file not found: {delay_cuts_path}")
            result["delay_cuts"] = None
            result["delay_cuts_path"] = None
        
        # 音频文件
        audio_path = output_dir / f"{prefix}_audio_a.mp3"
        if audio_path.exists():
            result["audio_a_path"] = audio_path
            logger.info(f"Audio file found: {audio_path}")
        else:
            logger.warning(f"Audio file not found: {audio_path}")
            result["audio_a_path"] = None
        
        return result
    
    def _parse_script(self, content: str) -> list[dict]:
        """解析脚本内容为结构化数据
        
        脚本格式示例:
        ```
        第一句文案内容
        第二句文案内容
        ```
        
        Args:
            content: 脚本文本内容
            
        Returns:
            list[dict]: 脚本段落列表
                - index: 段落索引
                - text: 段落文本
        """
        lines = content.strip().split('\n')
        segments = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                segments.append({
                    "index": i,
                    "text": line,
                })
        
        return segments
    
    async def upload_output(self, result: dict) -> None:
        """上传产物并更新数据库
        
        上传产物到 TOS (key: smart-cut/{task_id}/analyze/{filename})
        更新 SmartCutEdit:
            - status = "success"
            - audio_a_url
            - delay_cuts_tos_key
        更新 SmartCutTask:
            - analyze_script (解析 script.txt)
            - asr_result_tos_key
        
        Args:
            result: execute 方法返回的产物信息
            
        Raises:
            RuntimeError: 上传失败
        """
        if not self._current_task:
            raise RuntimeError("No task set")
        
        task_id = self._task_id
        upload_results = {}
        
        # 上传脚本
        if result.get("script_path"):
            key = f"smart-cut/{task_id}/analyze/script.json"
            self._upload_to_tos(result["script_path"], key)
            upload_results["script"] = key
            logger.info(f"Script uploaded: {key}")
        
        # 上传ASR结果
        if result.get("asr_path"):
            key = f"smart-cut/{task_id}/analyze/asr.json"
            self._upload_to_tos(result["asr_path"], key)
            upload_results["asr"] = key
            logger.info(f"ASR uploaded: {key}")
        
        # 上传延迟切割配置
        if result.get("delay_cuts_path"):
            key = f"smart-cut/{task_id}/analyze/delay_cuts.json"
            self._upload_to_tos(result["delay_cuts_path"], key)
            upload_results["delay_cuts"] = key
            logger.info(f"Delay cuts uploaded: {key}")
        
        # 上传音频
        if result.get("audio_a_path"):
            key = f"smart-cut/{task_id}/analyze/audio_a.mp3"
            self._upload_to_tos(result["audio_a_path"], key)
            upload_results["audio_a"] = key
            logger.info(f"Audio uploaded: {key}")
        
        # 更新数据库
        await self._update_database(result, upload_results)
        self.job_contract.write_result_manifest(
            task_id=task_id,
            scheduler_task_id=self._current_task.id,
            stage="analyze",
            status="success",
            outputs={
                "script": {
                    "local_path": str(result["script_path"]) if result.get("script_path") else None,
                    "tos_key": upload_results.get("script"),
                },
                "asr_result": {
                    "local_path": str(result["asr_path"]) if result.get("asr_path") else None,
                    "tos_key": upload_results.get("asr"),
                },
                "delay_cuts": {
                    "local_path": str(result["delay_cuts_path"]) if result.get("delay_cuts_path") else None,
                    "tos_key": upload_results.get("delay_cuts"),
                },
                "audio_a": {
                    "local_path": str(result["audio_a_path"]) if result.get("audio_a_path") else None,
                    "tos_key": upload_results.get("audio_a"),
                },
            },
        )
    
    async def _update_database(
        self,
        result: dict[str, Any],
        upload_results: dict[str, str]
    ) -> None:
        """更新数据库记录
        
        Args:
            result: 产物数据
            upload_results: 上传结果映射
        """
        db = self.get_db_session()
        try:
            # 更新业务任务
            business_task = db.query(BusinessTask).filter_by(id=self._task_id).first()
            if business_task:
                business_task.status = TaskStatus.WAITING_USER
                business_task.current_stage = CurrentStage.USER_SELECT
                business_task.analyze_script = result.get("script")
                business_task.asr_result_tos_key = upload_results.get("asr")
                logger.info(f"Business task updated: {business_task.id}")
            
            # 创建 Edit 记录
            edit = SmartCutEdit(
                task_id=self._task_id,
                edited_script=result.get("script"),  # 初始编辑状态为 analyze 结果
                status=EditStatus.SUCCESS,
                audio_a_url=upload_results.get("audio_a"),
                delay_cuts_tos_key=upload_results.get("delay_cuts"),
                version_number=1,
            )
            db.add(edit)
            db.flush()
            if business_task:
                business_task.active_edit_id = edit.id
            
            db.commit()
            logger.info(f"Database updated for task: {self._task_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            db.close()
    
    async def _handle_failure(self, error_message: str) -> None:
        """处理失败情况
        
        Args:
            error_message: 错误信息
        """
        db = self.get_db_session()
        try:
            if self._current_task and self._task_id:
                self.job_contract.write_result_manifest(
                    task_id=self._task_id,
                    scheduler_task_id=self._current_task.id,
                    stage="analyze",
                    status="failed",
                    outputs={},
                    error_message=error_message,
                )
            business_task = db.query(BusinessTask).filter_by(id=self._task_id).first()
            if business_task:
                business_task.status = TaskStatus.ANALYZE_FAILED
                business_task.failed_stage = "analyze"
                db.commit()
                logger.info(f"Task marked as analyze_failed: {business_task.id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update failure status: {e}")
        finally:
            db.close()
    
    def cleanup(self) -> None:
        """清理工作目录"""
        import shutil
        if self._work_dir and self._work_dir.exists():
            shutil.rmtree(self._work_dir)
            logger.info(f"Cleaned up work directory: {self._work_dir}")
