"""TOS Service - 火山引擎 TOS 对象存储服务封装

提供统一的 TOS 操作接口，支持真实 TOS 和本地 Fake 模式。
"""

import os
import shutil
import tempfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse

logger = logging.getLogger(__name__)


class TOSResult:
    """TOS 操作结果统一格式"""
    
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }
    
    def __repr__(self) -> str:
        return f"TOSResult(success={self.success}, data={self.data}, error={self.error})"


class FakeTOSClient:
    """Fake TOS 客户端 - 使用本地文件系统模拟 TOS"""
    
    def __init__(self, base_path: str):
        """初始化 Fake TOS 客户端
        
        Args:
            base_path: 本地存储根目录路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_object_path(self, bucket: str, key: str) -> Path:
        """获取对象的本地路径
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            Path: 本地文件路径
        """
        # 清理 key 中的前导斜杠
        key = key.lstrip('/')
        return self.base_path / bucket / key
    
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        operation: str,
        expires: int = 3600,
    ) -> str:
        """生成预签名 URL (Fake 模式返回本地文件路径)
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            operation: 操作类型 (put_object/get_object)
            expires: 过期时间（秒）
            
        Returns:
            str: 模拟的预签名 URL
        """
        object_path = self._get_object_path(bucket, key)
        expire_time = datetime.utcnow() + timedelta(seconds=expires)
        
        # 构建模拟的预签名 URL
        params = {
            "bucket": bucket,
            "key": key,
            "operation": operation,
            "expires": expire_time.isoformat(),
            "local_path": str(object_path.absolute()),
        }
        return f"fake://tos/{bucket}/{key}?{urlencode(params)}"
    
    def upload_file(self, bucket: str, key: str, file_path: str) -> dict:
        """上传本地文件
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            file_path: 本地文件路径
            
        Returns:
            dict: 上传结果信息
        """
        src_path = Path(file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")
        
        dst_path = self._get_object_path(bucket, key)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src_path, dst_path)
        
        return {
            "bucket": bucket,
            "key": key,
            "size": dst_path.stat().st_size,
            "etag": f"fake-etag-{dst_path.stat().st_mtime}",
            "last_modified": datetime.fromtimestamp(dst_path.stat().st_mtime).isoformat(),
        }
    
    def download_file(self, bucket: str, key: str, file_path: str) -> dict:
        """下载到本地
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            file_path: 本地目标路径
            
        Returns:
            dict: 下载结果信息
        """
        src_path = self._get_object_path(bucket, key)
        if not src_path.exists():
            raise FileNotFoundError(f"Object not found: {bucket}/{key}")
        
        dst_path = Path(file_path)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src_path, dst_path)
        
        return {
            "bucket": bucket,
            "key": key,
            "size": dst_path.stat().st_size,
            "local_path": str(dst_path.absolute()),
        }
    
    def check_object_exists(self, bucket: str, key: str) -> bool:
        """检查对象是否存在
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            bool: 对象是否存在
        """
        object_path = self._get_object_path(bucket, key)
        return object_path.exists() and object_path.is_file()
    
    def list_objects(self, bucket: str, prefix: str = "") -> list[dict]:
        """列出对象
        
        Args:
            bucket: 存储桶名称
            prefix: 前缀筛选
            
        Returns:
            list[dict]: 对象列表
        """
        bucket_path = self.base_path / bucket
        if not bucket_path.exists():
            return []
        
        objects = []
        prefix = prefix.lstrip('/')
        
        for file_path in bucket_path.rglob("*"):
            if file_path.is_file():
                # 计算相对 key
                relative_key = str(file_path.relative_to(bucket_path))
                
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
    
    def delete_object(self, bucket: str, key: str) -> bool:
        """删除对象
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            bool: 是否成功删除
        """
        object_path = self._get_object_path(bucket, key)
        if object_path.exists() and object_path.is_file():
            object_path.unlink()
            return True
        return False


class RealTOSClient:
    """真实 TOS 客户端 - 使用火山引擎官方 tos SDK"""
    
    def __init__(
        self,
        endpoint: str,
        region: str,
        access_key: str,
        secret_key: str,
    ):
        """初始化真实 TOS 客户端"""
        try:
            import tos
            from tos import HttpMethodType
        except ImportError:
            raise ImportError(
                "tos is required for real TOS mode. "
                "Install it with: pip install tos"
            )
        
        self._tos = tos
        self._http_method_type = HttpMethodType
        self.endpoint = endpoint
        self.region = region
        self.multipart_threshold_bytes = int(
            os.environ.get("TOS_MULTIPART_THRESHOLD_BYTES", str(32 * 1024 * 1024))
        )
        self.multipart_part_size = int(
            os.environ.get("TOS_MULTIPART_PART_SIZE_BYTES", str(5 * 1024 * 1024))
        )
        self.multipart_task_num = int(os.environ.get("TOS_MULTIPART_TASK_NUM", "1"))
        # TOS Python SDK defaults to a 30s socket timeout, which is too small for
        # A-machine -> TOS uploads on slow links. Keep the defaults conservative
        # but explicitly long so upload-direct can finish without hidden retries.
        self.socket_timeout_seconds = int(
            os.environ.get("TOS_SOCKET_TIMEOUT_SECONDS", "1800")
        )
        self.connection_timeout_seconds = int(
            os.environ.get("TOS_CONNECTION_TIMEOUT_SECONDS", "30")
        )
        self.max_retry_count = int(os.environ.get("TOS_MAX_RETRY_COUNT", "5"))
        self.upload_progress_log_step_percent = max(
            1,
            int(os.environ.get("TOS_UPLOAD_PROGRESS_LOG_STEP_PERCENT", "5")),
        )
        self.client = tos.TosClientV2(
            access_key,
            secret_key,
            endpoint,
            region,
            max_retry_count=self.max_retry_count,
            connection_time=self.connection_timeout_seconds,
            socket_timeout=self.socket_timeout_seconds,
        )

    def _build_progress_listener(self, bucket: str, key: str, file_size: int):
        last_logged_percent = -1

        def _listener(consumed_bytes: int, total_bytes: int, _rw_once_bytes: int, event_type) -> None:
            nonlocal last_logged_percent

            if total_bytes <= 0:
                total_bytes = file_size
            if total_bytes <= 0:
                return

            percent = min(100, int((consumed_bytes / total_bytes) * 100))
            if percent < 100 and percent // self.upload_progress_log_step_percent == last_logged_percent // self.upload_progress_log_step_percent:
                return

            last_logged_percent = percent
            logger.info(
                "tos multipart progress bucket=%s key=%s consumed=%s total=%s percent=%s event=%s",
                bucket,
                key,
                consumed_bytes,
                total_bytes,
                percent,
                getattr(event_type, "name", str(event_type)),
            )

        return _listener

    @staticmethod
    def _log_upload_event(event_type, error, bucket, key, upload_id, file_path, checkpoint_file, part_info) -> None:
        part_number = getattr(part_info, "part_number", None)
        part_size = getattr(part_info, "part_size", None)
        event_name = getattr(event_type, "name", str(event_type))
        if error is not None:
            logger.warning(
                "tos multipart event=%s bucket=%s key=%s upload_id=%s part_number=%s part_size=%s file_path=%s checkpoint=%s error=%s",
                event_name,
                bucket,
                key,
                upload_id,
                part_number,
                part_size,
                file_path,
                checkpoint_file,
                error,
            )
            return
        logger.info(
            "tos multipart event=%s bucket=%s key=%s upload_id=%s part_number=%s part_size=%s file_path=%s checkpoint=%s",
            event_name,
            bucket,
            key,
            upload_id,
            part_number,
            part_size,
            file_path,
            checkpoint_file,
        )
    
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        operation: str,
        expires: int = 3600,
    ) -> str:
        """生成预签名 URL"""
        http_method = (
            self._http_method_type.Http_Method_Put
            if operation == "put_object"
            else self._http_method_type.Http_Method_Get
        )
        result = self.client.pre_signed_url(
            http_method=http_method,
            bucket=bucket,
            key=key,
            expires=expires,
        )
        return result.signed_url
    
    def upload_file(self, bucket: str, key: str, file_path: str) -> dict:
        """上传本地文件"""
        file_size = Path(file_path).stat().st_size
        checkpoint_file: str | None = None

        try:
            if file_size >= self.multipart_threshold_bytes:
                with tempfile.NamedTemporaryFile(prefix="tos-upload-", suffix=".checkpoint", delete=False) as handle:
                    checkpoint_file = handle.name

                self.client.upload_file(
                    bucket,
                    key,
                    file_path,
                    part_size=self.multipart_part_size,
                    task_num=self.multipart_task_num,
                    enable_checkpoint=True,
                    checkpoint_file=checkpoint_file,
                    data_transfer_listener=self._build_progress_listener(bucket, key, file_size),
                    upload_event_listener=self._log_upload_event,
                )
            else:
                self.client.put_object_from_file(bucket, key, file_path)
        finally:
            if checkpoint_file and os.path.exists(checkpoint_file):
                os.unlink(checkpoint_file)

        response = self.client.head_object(bucket, key)
        
        return {
            "bucket": bucket,
            "key": key,
            "size": getattr(response, "content_length", 0),
            "etag": (getattr(response, "etag", "") or "").strip('"'),
            "last_modified": getattr(response, "last_modified", None),
            "upload_strategy": "multipart" if file_size >= self.multipart_threshold_bytes else "single_put",
        }
    
    def download_file(self, bucket: str, key: str, file_path: str) -> dict:
        """下载到本地"""
        self.client.get_object_to_file(bucket, key, file_path)
        
        file_size = Path(file_path).stat().st_size
        
        return {
            "bucket": bucket,
            "key": key,
            "size": file_size,
            "local_path": str(Path(file_path).absolute()),
        }
    
    def check_object_exists(self, bucket: str, key: str) -> bool:
        """检查对象是否存在"""
        try:
            self.client.head_object(bucket, key)
            return True
        except Exception:
            return False
    
    def list_objects(self, bucket: str, prefix: str = "") -> list[dict]:
        """列出对象"""
        objects = []
        result = self.client.list_objects(bucket=bucket, prefix=prefix, max_keys=1000)
        for obj in getattr(result, "contents", []) or []:
            objects.append(
                {
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": (obj.etag or "").strip('"'),
                }
            )
        
        return objects
    
    def delete_object(self, bucket: str, key: str) -> bool:
        """删除对象"""
        try:
            self.client.delete_object(bucket, key)
            return True
        except Exception:
            return False


class TOSService:
    """TOS 服务类
    
    封装所有与 TOS 对象存储相关的业务逻辑，支持真实模式和 Fake 模式。
    """
    
    def __init__(
        self,
        use_fake: bool = False,
        fake_base_path: Optional[str] = None,
        endpoint: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """初始化 TOS 服务
        
        Args:
            use_fake: 是否使用 Fake 模式（本地文件系统模拟）
            fake_base_path: Fake 模式下的本地存储根目录
            endpoint: 真实 TOS 端点 URL
            region: 真实 TOS 区域
            access_key: 真实 TOS 访问密钥
            secret_key: 真实 TOS 密钥
        """
        self.use_fake = use_fake
        
        if use_fake:
            # Fake 模式：使用本地文件系统
            base_path = fake_base_path or os.environ.get('FAKE_TOS_BASE_PATH', '/tmp/fake_tos')
            self._client = FakeTOSClient(base_path)
        else:
            # 真实模式：使用 boto3
            endpoint = endpoint or os.environ.get('TOS_ENDPOINT')
            region = region or os.environ.get('TOS_REGION', 'cn-beijing')
            access_key = access_key or os.environ.get('TOS_ACCESS_KEY')
            secret_key = secret_key or os.environ.get('TOS_SECRET_KEY')
            
            if not all([endpoint, access_key, secret_key]):
                raise ValueError(
                    "Real TOS mode requires endpoint, access_key, and secret_key. "
                    "Provide them as arguments or set environment variables."
                )
            
            self._client = RealTOSClient(
                endpoint=endpoint,
                region=region,
                access_key=access_key,
                secret_key=secret_key,
            )
    
    def generate_upload_url(
        self,
        bucket: str,
        key: str,
        expires: int = 3600,
    ) -> TOSResult:
        """生成预签名上传 URL
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            expires: URL 过期时间（秒），默认 3600
            
        Returns:
            TOSResult: 包含预签名 URL 的结果对象
        """
        try:
            url = self._client.generate_presigned_url(
                bucket=bucket,
                key=key,
                operation='put_object',
                expires=expires,
            )
            return TOSResult(
                success=True,
                data={"url": url, "bucket": bucket, "key": key, "expires": expires},
                metadata={"expires_at": (datetime.utcnow() + timedelta(seconds=expires)).isoformat()},
            )
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def generate_download_url(
        self,
        bucket: str,
        key: str,
        expires: int = 3600,
    ) -> TOSResult:
        """生成预签名下载 URL
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            expires: URL 过期时间（秒），默认 3600
            
        Returns:
            TOSResult: 包含预签名 URL 的结果对象
        """
        try:
            url = self._client.generate_presigned_url(
                bucket=bucket,
                key=key,
                operation='get_object',
                expires=expires,
            )
            return TOSResult(
                success=True,
                data={"url": url, "bucket": bucket, "key": key, "expires": expires},
                metadata={"expires_at": (datetime.utcnow() + timedelta(seconds=expires)).isoformat()},
            )
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def upload_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> TOSResult:
        """上传本地文件
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            file_path: 本地文件路径
            
        Returns:
            TOSResult: 上传结果
        """
        try:
            result = self._client.upload_file(bucket, key, file_path)
            return TOSResult(
                success=True,
                data=result,
                metadata={"operation": "upload"},
            )
        except FileNotFoundError as e:
            return TOSResult(success=False, error=f"File not found: {e}")
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def download_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> TOSResult:
        """下载到本地
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            file_path: 本地目标路径
            
        Returns:
            TOSResult: 下载结果
        """
        try:
            result = self._client.download_file(bucket, key, file_path)
            return TOSResult(
                success=True,
                data=result,
                metadata={"operation": "download"},
            )
        except FileNotFoundError as e:
            return TOSResult(success=False, error=f"Object not found: {e}")
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def check_object_exists(
        self,
        bucket: str,
        key: str,
    ) -> TOSResult:
        """检查对象是否存在
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            TOSResult: 包含存在状态的结果对象
        """
        try:
            exists = self._client.check_object_exists(bucket, key)
            return TOSResult(
                success=True,
                data={"exists": exists, "bucket": bucket, "key": key},
            )
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> TOSResult:
        """列出对象
        
        Args:
            bucket: 存储桶名称
            prefix: 前缀筛选（可选）
            
        Returns:
            TOSResult: 包含对象列表的结果对象
        """
        try:
            objects = self._client.list_objects(bucket, prefix)
            return TOSResult(
                success=True,
                data={
                    "objects": objects,
                    "count": len(objects),
                    "bucket": bucket,
                    "prefix": prefix,
                },
            )
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def delete_object(
        self,
        bucket: str,
        key: str,
    ) -> TOSResult:
        """删除对象
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            TOSResult: 删除结果
        """
        try:
            deleted = self._client.delete_object(bucket, key)
            return TOSResult(
                success=deleted,
                data={"deleted": deleted, "bucket": bucket, "key": key},
                error=None if deleted else "Object not found or could not be deleted",
            )
        except Exception as e:
            return TOSResult(success=False, error=str(e))
    
    def upload_content(
        self,
        bucket: str,
        key: str,
        content: bytes,
    ) -> TOSResult:
        """直接上传字节内容
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            content: 字节内容
            
        Returns:
            TOSResult: 上传结果
        """
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            result = self._client.upload_file(bucket, key, temp_path)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            return TOSResult(
                success=True,
                data=result,
                metadata={"operation": "upload_content", "size": len(content)},
            )
        except Exception as e:
            # 确保清理临时文件
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return TOSResult(success=False, error=str(e))
    
    def download_content(
        self,
        bucket: str,
        key: str,
    ) -> TOSResult:
        """直接下载字节内容
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            TOSResult: 包含字节内容的结果对象
        """
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_path = f.name
            
            result = self._client.download_file(bucket, key, temp_path)
            
            with open(temp_path, 'rb') as f:
                content = f.read()
            
            # 清理临时文件
            os.unlink(temp_path)
            
            return TOSResult(
                success=True,
                data={"content": content, "size": len(content), "bucket": bucket, "key": key},
                metadata={"operation": "download_content"},
            )
        except FileNotFoundError as e:
            # 确保清理临时文件
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return TOSResult(success=False, error=f"Object not found: {e}")
        except Exception as e:
            # 确保清理临时文件
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return TOSResult(success=False, error=str(e))
