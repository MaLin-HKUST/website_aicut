"""Fake TOS Service - 本地文件系统模拟 TOS

使用本地文件系统模拟火山引擎 TOS，便于本地开发和测试。
接口与真实 TOS 完全一致，便于切换。

路径结构: /fake-tos/smart-cut-e2e/{run_id}/
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from urllib.parse import urlencode


class FakeTOSService:
    """Fake TOS 服务类
    
    使用本地文件系统模拟 TOS，支持 run_id 隔离，
    接口与真实 TOS 完全一致，便于切换。
    
    Attributes:
        base_path: Fake TOS 根目录
        run_id: 当前运行 ID，用于测试隔离
        bucket: 存储桶名称，默认 smart-cut-e2e
    """
    
    def __init__(
        self,
        base_path: str = "/fake-tos",
        run_id: Optional[str] = None,
        bucket: str = "smart-cut-e2e",
    ):
        """初始化 Fake TOS 服务
        
        Args:
            base_path: Fake TOS 根目录，默认 /fake-tos
            run_id: 运行 ID，用于测试隔离，默认从环境变量获取
            bucket: 存储桶名称，默认 smart-cut-e2e
        """
        self.base_path = Path(base_path)
        self.run_id = run_id or os.environ.get("FAKE_TOS_RUN_ID", "default")
        self.bucket = bucket
        
        # 创建 run_id 隔离目录
        self.run_path = self.base_path / bucket / self.run_id
        self.run_path.mkdir(parents=True, exist_ok=True)
    
    def _get_object_path(self, object_key: str) -> Path:
        """获取对象的本地路径
        
        Args:
            object_key: 对象键名
            
        Returns:
            Path: 本地文件路径
        """
        # 清理 key 中的前导斜杠
        object_key = object_key.lstrip('/')
        return self.run_path / object_key
    
    def upload_file(self, local_path: str, object_key: str) -> str:
        """上传文件到 Fake TOS
        
        实际是本地文件复制到 Fake TOS 目录
        
        Args:
            local_path: 本地源文件路径
            object_key: 目标对象键名
            
        Returns:
            str: Fake TOS 文件 URL (file:// 协议)
            
        Raises:
            FileNotFoundError: 源文件不存在
        """
        src = Path(local_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {local_path}")
        
        dest = self._get_object_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src, dest)
        
        return f"file://{dest}"
    
    def download_file(self, object_key: str, local_path: str) -> str:
        """从 Fake TOS 下载文件
        
        实际是从 Fake TOS 目录复制到本地
        
        Args:
            object_key: 源对象键名
            local_path: 本地目标文件路径
            
        Returns:
            str: 本地文件路径
            
        Raises:
            FileNotFoundError: 对象不存在
        """
        src = self._get_object_path(object_key)
        if not src.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src, dest)
        
        return str(dest)
    
    def generate_presigned_url(self, object_key: str, expiration: int = 3600) -> str:
        """生成预签名 URL
        
        Fake 模式下返回本地文件路径作为模拟 URL
        
        Args:
            object_key: 对象键名
            expiration: 过期时间（秒），默认 3600，仅用于模拟
            
        Returns:
            str: 模拟的预签名 URL
        """
        object_path = self._get_object_path(object_key)
        expire_time = datetime.utcnow().timestamp() + expiration
        
        params = {
            "bucket": self.bucket,
            "key": object_key,
            "run_id": self.run_id,
            "expires": int(expire_time),
            "local_path": str(object_path.absolute()),
        }
        
        return f"fake://tos/{self.bucket}/{self.run_id}/{object_key}?{urlencode(params)}"
    
    def check_object_exists(self, object_key: str) -> bool:
        """检查对象是否存在
        
        Args:
            object_key: 对象键名
            
        Returns:
            bool: 对象是否存在且为文件
        """
        object_path = self._get_object_path(object_key)
        return object_path.exists() and object_path.is_file()
    
    def list_objects(self, prefix: str = "") -> list[dict]:
        """列出对象
        
        Args:
            prefix: 前缀筛选（可选）
            
        Returns:
            list[dict]: 对象列表，每个对象包含 key, size, last_modified, etag
        """
        if not self.run_path.exists():
            return []
        
        objects = []
        prefix = prefix.lstrip('/')
        
        for file_path in self.run_path.rglob("*"):
            if file_path.is_file():
                # 计算相对 key
                relative_key = str(file_path.relative_to(self.run_path))
                
                # 前缀筛选
                if prefix and not relative_key.startswith(prefix):
                    continue
                
                stat = file_path.stat()
                objects.append({
                    "key": relative_key,
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "etag": f"fake-etag-{stat.st_mtime}",
                })
        
        # 按 key 排序
        objects.sort(key=lambda x: x["key"])
        return objects
    
    def delete_object(self, object_key: str) -> bool:
        """删除对象
        
        Args:
            object_key: 对象键名
            
        Returns:
            bool: 是否成功删除
        """
        object_path = self._get_object_path(object_key)
        if object_path.exists() and object_path.is_file():
            object_path.unlink()
            return True
        return False
    
    def delete_prefix(self, prefix: str) -> int:
        """删除指定前缀的所有对象
        
        Args:
            prefix: 对象键前缀
            
        Returns:
            int: 删除的对象数量
        """
        objects = self.list_objects(prefix)
        deleted_count = 0
        
        for obj in objects:
            if self.delete_object(obj["key"]):
                deleted_count += 1
        
        return deleted_count
    
    def get_object_size(self, object_key: str) -> int:
        """获取对象大小
        
        Args:
            object_key: 对象键名
            
        Returns:
            int: 对象大小（字节）
            
        Raises:
            FileNotFoundError: 对象不存在
        """
        object_path = self._get_object_path(object_key)
        if not object_path.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        
        return object_path.stat().st_size
    
    def get_object_metadata(self, object_key: str) -> dict:
        """获取对象元数据
        
        Args:
            object_key: 对象键名
            
        Returns:
            dict: 对象元数据，包含 size, last_modified, etag
            
        Raises:
            FileNotFoundError: 对象不存在
        """
        object_path = self._get_object_path(object_key)
        if not object_path.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        
        stat = object_path.stat()
        return {
            "key": object_key,
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "etag": f"fake-etag-{stat.st_mtime}",
            "content_type": self._guess_content_type(object_key),
        }
    
    def _guess_content_type(self, object_key: str) -> str:
        """猜测文件内容类型
        
        Args:
            object_key: 对象键名
            
        Returns:
            str: 内容类型 MIME
        """
        import mimetypes
        content_type, _ = mimetypes.guess_type(object_key)
        return content_type or "application/octet-stream"
    
    def upload_content(self, content: bytes, object_key: str) -> str:
        """直接上传字节内容
        
        Args:
            content: 字节内容
            object_key: 目标对象键名
            
        Returns:
            str: Fake TOS 文件 URL
        """
        dest = self._get_object_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest, 'wb') as f:
            f.write(content)
        
        return f"file://{dest}"
    
    def download_content(self, object_key: str) -> bytes:
        """直接下载字节内容
        
        Args:
            object_key: 对象键名
            
        Returns:
            bytes: 对象内容
            
        Raises:
            FileNotFoundError: 对象不存在
        """
        object_path = self._get_object_path(object_key)
        if not object_path.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        
        with open(object_path, 'rb') as f:
            return f.read()
    
    def cleanup_run(self) -> int:
        """清理当前 run_id 的所有数据
        
        Returns:
            int: 删除的文件数量
        """
        if not self.run_path.exists():
            return 0
        
        deleted_count = 0
        for file_path in self.run_path.rglob("*"):
            if file_path.is_file():
                file_path.unlink()
                deleted_count += 1
        
        # 清理空目录
        for dir_path in sorted(self.run_path.rglob("*"), key=lambda p: len(str(p)), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
        
        return deleted_count
    
    def get_run_path(self) -> str:
        """获取当前 run_id 的完整路径
        
        Returns:
            str: 本地路径字符串
        """
        return str(self.run_path)


# 便捷函数：快速创建 Fake TOS 服务实例
def create_fake_tos_service(
    run_id: Optional[str] = None,
    base_path: Optional[str] = None,
) -> FakeTOSService:
    """创建 Fake TOS 服务实例
    
    从环境变量或参数创建 FakeTOSService 实例
    
    Args:
        run_id: 运行 ID，默认从 FAKE_TOS_RUN_ID 环境变量获取
        base_path: 根路径，默认从 FAKE_TOS_BASE_PATH 环境变量获取或 /fake-tos
        
    Returns:
        FakeTOSService: Fake TOS 服务实例
    """
    return FakeTOSService(
        base_path=base_path or os.environ.get("FAKE_TOS_BASE_PATH", "/fake-tos"),
        run_id=run_id or os.environ.get("FAKE_TOS_RUN_ID"),
        bucket=os.environ.get("FAKE_TOS_BUCKET", "smart-cut-e2e"),
    )
