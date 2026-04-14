"""Base Processor - Worker 任务处理器基类

定义所有任务处理器的通用接口和基础功能。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import os
import logging
from pathlib import Path

from apps.models.scheduler_task import SchedulerTask
from worker.services import GatewayFileTransport


logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """任务处理器基类
    
    所有具体的任务处理器（analyze、preview、finalize）都需要继承此类，
    并实现 process 方法。
    
    提供通用功能：
    - 输入文件下载
    - 产物上传
    - 进度更新
    """
    
    def __init__(self, tos_service: Any, workspace: str):
        """初始化处理器
        
        Args:
            tos_service: TOS 服务对象，用于文件上传下载
            workspace: 工作目录路径
        """
        self.tos_service = tos_service
        self.workspace = workspace
        self._current_task: Optional[SchedulerTask] = None
        self._progress_callback: Optional[callable] = None
        self.file_transport = GatewayFileTransport(
            tos_service=tos_service,
            workspace=workspace,
        )
        
        # 确保工作目录存在
        os.makedirs(workspace, exist_ok=True)
    
    def set_task(self, task: SchedulerTask) -> None:
        """设置当前任务
        
        Args:
            task: 调度任务对象
        """
        self._current_task = task
    
    def set_progress_callback(self, callback: callable) -> None:
        """设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收 progress: float 参数
        """
        self._progress_callback = callback
    
    @abstractmethod
    async def process(self, task: SchedulerTask, workspace: str) -> dict[str, Any]:
        """处理任务 - 子类必须实现
        
        Args:
            task: 调度任务对象
            workspace: 工作目录路径
            
        Returns:
            dict: 处理结果，包含输出文件信息等
            
        Raises:
            Exception: 处理失败时抛出异常
        """
        pass
    
    def download_inputs(self, payload: dict[str, Any]) -> dict[str, str]:
        """下载输入文件
        
        从 payload 中识别文件路径，下载到本地工作目录。
        支持的文件路径字段：
        - video_key, video_path: 视频文件
        - text_key, text_path: 文本文件
        - audio_key, audio_path: 音频文件
        - script_key, script_path: 脚本文件
        - edit_key, edit_path: 编辑配置
        - *key, *path: 其他以 _key 或 _path 结尾的字段
        
        Args:
            payload: 任务参数
            
        Returns:
            dict: 本地文件路径映射 {原始key: 本地路径}
        """
        local_paths = {}
        
        for key, value in payload.items():
            if not isinstance(value, str):
                continue
                
            # 识别文件路径字段
            if key.endswith('_key') or key.endswith('_path'):
                try:
                    local_path = self._download_file(value)
                    if local_path:
                        local_paths[key] = local_path
                        logger.info(f"Downloaded {key}: {value} -> {local_path}")
                except Exception as e:
                    logger.error(f"Failed to download {key}: {value}, error: {e}")
                    raise
        
        return local_paths

    async def download_input_file(self, source: str, local_path: str) -> str:
        """Download one input into the gateway workspace."""
        downloaded_path = await self.file_transport.download_input(source, Path(local_path))
        return str(downloaded_path)

    async def upload_output_file(self, local_path: str, key: str) -> str:
        """Upload one output from the gateway workspace."""
        uploaded_key = await self.file_transport.upload_output(Path(local_path), key)
        return uploaded_key
    
    def _download_file(self, remote_path: str) -> Optional[str]:
        """下载单个文件
        
        Args:
            remote_path: 远程文件路径（TOS key）
            
        Returns:
            str: 本地文件路径，失败返回 None
        """
        if not remote_path or not isinstance(remote_path, str):
            return None
            
        # 如果已经是本地路径，直接返回
        if os.path.exists(remote_path):
            return remote_path
            
        # 构建本地路径
        filename = os.path.basename(remote_path)
        local_path = os.path.join(self.workspace, filename)
        
        # 如果 tos_service 存在且可用，下载文件
        if self.tos_service and hasattr(self.tos_service, 'download'):
            try:
                self.tos_service.download(remote_path, local_path)
                return local_path
            except Exception as e:
                logger.warning(f"TOS download failed for {remote_path}: {e}")
                # 如果下载失败但远程路径可能是本地路径，返回原值
                return remote_path
        
        # 没有 tos_service，假设路径是本地路径
        return remote_path
    
    def upload_outputs(self, outputs: dict[str, Any]) -> dict[str, str]:
        """上传产物文件
        
        将本地文件上传到 TOS，返回远程路径映射。
        
        Args:
            outputs: 输出文件映射 {key: 本地路径或数据}
            
        Returns:
            dict: 远程路径映射 {key: 远程路径}
        """
        remote_paths = {}
        
        for key, value in outputs.items():
            if isinstance(value, str) and os.path.isfile(value):
                # 是本地文件路径，上传
                try:
                    remote_path = self._upload_file(value)
                    remote_paths[key] = remote_path
                    logger.info(f"Uploaded {key}: {value} -> {remote_path}")
                except Exception as e:
                    logger.error(f"Failed to upload {key}: {value}, error: {e}")
                    raise
            else:
                # 非文件类型数据，直接保留
                remote_paths[key] = value
        
        return remote_paths
    
    def _upload_file(self, local_path: str) -> str:
        """上传单个文件
        
        Args:
            local_path: 本地文件路径
            
        Returns:
            str: 远程文件路径（TOS key）
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        # 如果 tos_service 存在且可用，上传文件
        if self.tos_service and hasattr(self.tos_service, 'upload'):
            try:
                # 生成远程路径
                filename = os.path.basename(local_path)
                task_id = self._current_task.id if self._current_task else "unknown"
                remote_path = f"smart-cut/{task_id}/output/{filename}"
                
                self.tos_service.upload(local_path, remote_path)
                return remote_path
            except Exception as e:
                logger.error(f"TOS upload failed: {e}")
                raise
        
        # 没有 tos_service，返回本地路径
        return local_path
    
    def update_progress(self, progress: float) -> None:
        """更新任务进度
        
        Args:
            progress: 进度值 (0.0 - 1.0)
            
        Note:
            可以通过 set_progress_callback 设置回调函数，
            将进度上报给 Worker 或调度器。
        """
        # 确保进度在有效范围内
        progress = max(0.0, min(1.0, progress))
        
        logger.debug(f"Task progress: {progress * 100:.1f}%")
        
        # 调用回调函数
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def cleanup(self) -> None:
        """清理工作目录
        
        可选的清理操作，子类可以重写此方法。
        """
        # 默认不清理，子类可以选择实现
        pass
