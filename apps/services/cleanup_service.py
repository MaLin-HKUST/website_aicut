"""Cleanup Service - 测试和工作空间清理服务

提供测试前/后清理、任务工作空间清理、放弃任务清理等功能。

路径结构:
- Fake TOS: /fake-tos/{bucket}/{run_id}/
- 工作目录: /data/smart-cut/{task_id}/
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from apps.models.task import SmartCutTask


class CleanupService:
    """测试清理服务
    
    管理测试环境和工作空间的清理，确保测试隔离性和资源释放。
    
    Attributes:
        fake_tos_base_path: Fake TOS 根目录
        workspace_base_path: 工作空间根目录
    """
    
    def __init__(
        self,
        fake_tos_base_path: str = "/fake-tos",
        workspace_base_path: str = "/data/smart-cut",
    ):
        """初始化清理服务
        
        Args:
            fake_tos_base_path: Fake TOS 根目录，默认 /fake-tos
            workspace_base_path: 工作空间根目录，默认 /data/smart-cut
        """
        self.fake_tos_base_path = Path(fake_tos_base_path)
        self.workspace_base_path = Path(workspace_base_path)
    
    def cleanup_before_test(self, run_id: str) -> dict:
        """测试前清理
        
        清理指定 run_id 的测试环境，确保测试开始时环境干净。
        
        Args:
            run_id: 测试运行 ID
            
        Returns:
            dict: 清理结果统计
                - fake_tos_cleaned: 清理的 Fake TOS 文件数
                - workspaces_cleaned: 清理的工作空间数
        """
        result = {
            "fake_tos_cleaned": 0,
            "workspaces_cleaned": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 1. 清理 Fake TOS 中该 run_id 的所有数据
        fake_tos_path = self.fake_tos_base_path / run_id
        if fake_tos_path.exists():
            result["fake_tos_cleaned"] = self._delete_directory_contents(fake_tos_path)
        
        # 2. 清理工作目录中所有测试任务（通过命名约定识别）
        # 测试任务通常使用 test- 或 test_ 前缀
        if self.workspace_base_path.exists():
            for item in self.workspace_base_path.iterdir():
                if item.is_dir() and (
                    item.name.startswith("test-") or 
                    item.name.startswith("test_") or
                    "-test-" in item.name
                ):
                    shutil.rmtree(item, ignore_errors=True)
                    result["workspaces_cleaned"] += 1
        
        return result
    
    def cleanup_after_test(self, run_id: str, task_ids: list[str]) -> dict:
        """测试后清理
        
        清理测试产生的所有数据，包括 Fake TOS 目录和本地工作目录。
        
        Args:
            run_id: 测试运行 ID
            task_ids: 测试中创建的任务 ID 列表
            
        Returns:
            dict: 清理结果统计
                - fake_tos_cleaned: 清理的 Fake TOS 文件数
                - workspaces_cleaned: 清理的工作空间数
                - tasks_cleaned: 清理的任务工作空间数
        """
        result = {
            "fake_tos_cleaned": 0,
            "workspaces_cleaned": 0,
            "tasks_cleaned": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 1. 清理 Fake TOS 目录
        fake_tos_path = self.fake_tos_base_path / run_id
        if fake_tos_path.exists():
            result["fake_tos_cleaned"] = self._delete_directory_contents(fake_tos_path)
            # 删除空的 run_id 目录
            try:
                fake_tos_path.rmdir()
            except OSError:
                pass  # 目录不为空时忽略
        
        # 2. 清理指定任务的工作空间
        for task_id in task_ids:
            task_result = self.cleanup_task_workspace(task_id)
            if task_result["success"]:
                result["tasks_cleaned"] += 1
        
        # 3. 清理其他临时工作目录
        if self.workspace_base_path.exists():
            for item in self.workspace_base_path.iterdir():
                if item.is_dir() and item.name.startswith(f"temp-{run_id}"):
                    shutil.rmtree(item, ignore_errors=True)
                    result["workspaces_cleaned"] += 1
        
        return result
    
    def cleanup_task_workspace(self, task_id: str) -> dict:
        """清理单个任务工作空间
        
        删除指定任务的所有本地工作文件。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            dict: 清理结果
                - success: 是否成功
                - files_deleted: 删除的文件数
                - path: 清理的路径
        """
        result = {
            "success": False,
            "files_deleted": 0,
            "path": None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        workspace_path = self.workspace_base_path / task_id
        result["path"] = str(workspace_path)
        
        if not workspace_path.exists():
            return result  # 路径不存在，视为已清理
        
        result["files_deleted"] = self._delete_directory_contents(workspace_path)
        
        # 尝试删除空目录
        try:
            shutil.rmtree(workspace_path)
            result["success"] = True
        except OSError as e:
            result["error"] = str(e)
        
        return result
    
    def cleanup_abandoned_task(self, task: SmartCutTask) -> dict:
        """清理放弃的任务
        
        清理任务的工作目录，可选清理 TOS 上的中间产物。
        
        Args:
            task: SmartCutTask 对象
            
        Returns:
            dict: 清理结果
                - task_id: 任务 ID
                - workspace_cleaned: 工作空间是否已清理
                - tos_cleaned: 是否清理了 TOS 产物
                - details: 详细信息
        """
        result = {
            "task_id": task.id,
            "workspace_cleaned": False,
            "tos_cleaned": False,
            "details": {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 1. 清理工作空间
        workspace_result = self.cleanup_task_workspace(task.id)
        result["workspace_cleaned"] = workspace_result["success"]
        result["details"]["workspace"] = workspace_result
        
        # 2. 清理 Fake TOS 上的任务相关对象
        # 删除 tasks/{task_id}/ 前缀的所有对象
        tos_path = self.fake_tos_base_path / "smart-cut-uploads" / f"tasks/{task.id}"
        if tos_path.exists():
            tos_deleted = self._delete_directory_contents(tos_path)
            try:
                shutil.rmtree(tos_path)
                result["tos_cleaned"] = True
                result["details"]["tos_files_deleted"] = tos_deleted
            except OSError as e:
                result["details"]["tos_error"] = str(e)
        
        # 3. 清理 ASR 结果（如果存在）
        if task.asr_result_tos_key:
            asr_path = self.fake_tos_base_path / "smart-cut-uploads" / task.asr_result_tos_key
            if asr_path.exists():
                try:
                    asr_path.unlink()
                    result["details"]["asr_result_deleted"] = True
                except OSError as e:
                    result["details"]["asr_result_error"] = str(e)
        
        return result
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> dict:
        """清理过期的任务工作空间
        
        清理超过指定时间的任务工作目录。
        
        Args:
            max_age_hours: 最大保留时间（小时），默认 24 小时
            
        Returns:
            dict: 清理结果统计
                - cleaned_count: 清理的任务数
                - cleaned_task_ids: 清理的任务 ID 列表
        """
        result = {
            "cleaned_count": 0,
            "cleaned_task_ids": [],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if not self.workspace_base_path.exists():
            return result
        
        now = datetime.utcnow().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        for item in self.workspace_base_path.iterdir():
            if not item.is_dir():
                continue
            
            # 检查目录修改时间
            try:
                stat = item.stat()
                age_seconds = now - stat.st_mtime
                
                if age_seconds > max_age_seconds:
                    shutil.rmtree(item, ignore_errors=True)
                    result["cleaned_count"] += 1
                    result["cleaned_task_ids"].append(item.name)
            except OSError:
                continue
        
        return result
    
    def get_cleanup_summary(self) -> dict:
        """获取清理统计摘要
        
        Returns:
            dict: 当前存储使用情况统计
        """
        summary = {
            "fake_tos_path": str(self.fake_tos_base_path),
            "workspace_path": str(self.workspace_base_path),
            "fake_tos_size_bytes": 0,
            "workspace_size_bytes": 0,
            "workspace_task_count": 0,
        }
        
        # 计算 Fake TOS 大小
        if self.fake_tos_base_path.exists():
            summary["fake_tos_size_bytes"] = self._get_directory_size(self.fake_tos_base_path)
        
        # 计算工作空间大小
        if self.workspace_base_path.exists():
            summary["workspace_size_bytes"] = self._get_directory_size(self.workspace_base_path)
            summary["workspace_task_count"] = sum(
                1 for item in self.workspace_base_path.iterdir() if item.is_dir()
            )
        
        return summary
    
    def _delete_directory_contents(self, path: Path) -> int:
        """删除目录下的所有内容（包括子目录中的文件，但不包括目录本身）
        
        Args:
            path: 目标目录路径
            
        Returns:
            int: 删除的文件数
        """
        deleted_count = 0
        
        if not path.exists():
            return deleted_count
        
        # 首先收集所有文件和目录
        files_to_delete = []
        dirs_to_delete = []
        
        for item in path.rglob("*"):
            if item.is_file():
                files_to_delete.append(item)
            elif item.is_dir() and item != path:
                dirs_to_delete.append(item)
        
        # 删除所有文件
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except OSError:
                continue
        
        # 按深度排序目录（先删除深层目录）
        dirs_to_delete.sort(key=lambda p: len(str(p)), reverse=True)
        for dir_path in dirs_to_delete:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except OSError:
                continue
        
        return deleted_count
    
    def _get_directory_size(self, path: Path) -> int:
        """计算目录大小
        
        Args:
            path: 目标目录路径
            
        Returns:
            int: 目录大小（字节）
        """
        total_size = 0
        
        if not path.exists():
            return total_size
        
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                except OSError:
                    continue
        
        return total_size


# 便捷函数：快速创建清理服务实例
def create_cleanup_service(
    fake_tos_base_path: Optional[str] = None,
    workspace_base_path: Optional[str] = None,
) -> CleanupService:
    """创建清理服务实例
    
    从环境变量或参数创建 CleanupService 实例
    
    Args:
        fake_tos_base_path: Fake TOS 根路径，默认从 FAKE_TOS_BASE_PATH 环境变量获取或 /fake-tos
        workspace_base_path: 工作空间根路径，默认从 WORKSPACE_BASE_PATH 环境变量获取或 /data/smart-cut
        
    Returns:
        CleanupService: 清理服务实例
    """
    return CleanupService(
        fake_tos_base_path=fake_tos_base_path or os.environ.get("FAKE_TOS_BASE_PATH", "/fake-tos"),
        workspace_base_path=workspace_base_path or os.environ.get("WORKSPACE_BASE_PATH", "/data/smart-cut"),
    )
