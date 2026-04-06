"""
TOS 服务模块

支持 Fake TOS（宿主机挂载）和真实 TOS 的对象操作
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class TOSClient(Protocol):
    """TOS 客户端协议"""

    def object_exists(self, key: str) -> bool:
        """检查对象是否存在"""
        ...

    def get_object_url(self, key: str) -> str:
        """获取对象访问 URL"""
        ...


class FakeTOSClient:
    """
    Fake TOS 客户端

    使用宿主机挂载目录模拟 TOS
    根目录: /Volumes/XIAOMA-A-1T/docker_hub/FakeTos
    """

    def __init__(self, root_path: str = "/Volumes/XIAOMA-A-1T/docker_hub/FakeTos") -> None:
        self.root = Path(root_path)

    def object_exists(self, key: str) -> bool:
        """检查对象是否存在于 Fake TOS"""
        # 移除开头的斜杠
        key = key.lstrip("/")
        full_path = self.root / key
        return full_path.exists()

    def get_object_url(self, key: str) -> str:
        """获取 Fake TOS 对象的本地路径"""
        key = key.lstrip("/")
        return str(self.root / key)

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        """
        生成预签名 URL（Fake 模式返回本地文件路径）
        
        Args:
            key: 对象 key
            expires_in: 过期时间（秒，Fake 模式下忽略）
        
        Returns:
            本地文件路径，如果对象不存在则返回 None
        """
        key = key.lstrip("/")
        full_path = self.root / key
        if not full_path.exists():
            return None
        # Fake 模式返回 file:// 协议的路径
        return f"file://{full_path}"

    def ensure_directory(self, key: str) -> Path:
        """确保目录存在，返回目录路径"""
        key = key.lstrip("/")
        dir_path = self.root / key
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def put_object(self, key: str, content: bytes) -> None:
        """写入对象（用于测试）"""
        key = key.lstrip("/")
        full_path = self.root / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

    def delete_object(self, key: str) -> bool:
        """删除对象"""
        key = key.lstrip("/")
        full_path = self.root / key
        if full_path.exists():
            if full_path.is_file():
                full_path.unlink()
            else:
                import shutil
                shutil.rmtree(full_path)
            return True
        return False

    def list_objects(self, prefix: str) -> list[str]:
        """列出指定前缀下的所有对象"""
        prefix = prefix.lstrip("/")
        base_path = self.root / prefix
        if not base_path.exists():
            return []

        results = []
        for path in base_path.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(self.root)
                results.append(str(rel_path))
        return results


class RealTOSClient:
    """
    真实 TOS 客户端（占位实现）

    实际项目中应使用火山引擎 TOS SDK
    当前状态：未实现，调用会抛出 NotImplementedError
    """

    def __init__(self) -> None:
        # 从环境变量读取配置
        self.endpoint = os.getenv("TOS_ENDPOINT", "")
        self.region = os.getenv("TOS_REGION", "")
        self.bucket = os.getenv("TOS_BUCKET", "")
        self.access_key = os.getenv("TOS_ACCESS_KEY", "")
        self.secret_key = os.getenv("TOS_SECRET_KEY", "")

    def _ensure_initialized(self) -> None:
        """确保客户端已正确初始化"""
        if not all([self.endpoint, self.bucket, self.access_key, self.secret_key]):
            raise RuntimeError(
                "Real TOS client not properly configured. "
                "Please set TOS_ENDPOINT, TOS_BUCKET, TOS_ACCESS_KEY, TOS_SECRET_KEY environment variables."
            )

    def object_exists(self, key: str) -> bool:
        """检查对象是否存在于真实 TOS"""
        self._ensure_initialized()
        raise NotImplementedError(
            "Real TOS integration not implemented. "
            "Please implement using Volcano Engine TOS SDK or set use_fake_tos=True for testing."
        )

    def get_object_url(self, key: str) -> str:
        """获取对象访问 URL"""
        self._ensure_initialized()
        raise NotImplementedError(
            "Real TOS integration not implemented. "
            "Please implement using Volcano Engine TOS SDK."
        )

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        """
        生成预签名 URL（占位实现）
        
        实际项目中应使用火山引擎 TOS SDK 生成预签名 URL
        
        Args:
            key: 对象 key
            expires_in: 过期时间（秒）
        
        Returns:
            预签名 URL，如果对象不存在则返回 None
        """
        self._ensure_initialized()
        raise NotImplementedError(
            "Real TOS presigned URL generation not implemented. "
            "Please implement using Volcano Engine TOS SDK."
        )


def get_tos_client(use_fake: bool = True) -> TOSClient:
    """
    获取 TOS 客户端

    Args:
        use_fake: 使用 Fake TOS（测试模式）

    Returns:
        TOSClient 实例
    """
    if use_fake:
        return FakeTOSClient()
    return RealTOSClient()


def validate_tos_key_belongs_to_task(task_id: str, key: str) -> bool:
    """
    验证 TOS key 是否属于指定任务

    Key 格式要求: smart-cut/{task_id}/...
    """
    expected_prefix = f"smart-cut/{task_id}/"
    return key.startswith(expected_prefix)
