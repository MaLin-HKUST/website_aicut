"""TOS Service - 火山引擎 TOS 对象存储服务封装

提供统一的 TOS 操作接口，支持真实 TOS (S3 兼容) 和本地 Fake 模式。
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse


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
    """真实 TOS 客户端 - 使用 boto3 访问火山引擎 TOS"""
    
    def __init__(
        self,
        endpoint: str,
        region: str,
        access_key: str,
        secret_key: str,
    ):
        """初始化真实 TOS 客户端
        
        Args:
            endpoint: TOS 服务端点
            region: 区域
            access_key: 访问密钥
            secret_key: 密钥
        """
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for real TOS mode. "
                "Install it with: pip install boto3"
            )
        
        self.endpoint = endpoint
        self.region = region
        
        # 配置 boto3 客户端
        config = Config(
            region_name=region,
            signature_version='s3v4',
        )
        
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
        )
    
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        operation: str,
        expires: int = 3600,
    ) -> str:
        """生成预签名 URL"""
        client_method = 'put_object' if operation == 'put_object' else 'get_object'
        
        url = self.client.generate_presigned_url(
            ClientMethod=client_method,
            Params={
                'Bucket': bucket,
                'Key': key,
            },
            ExpiresIn=expires,
        )
        return url
    
    def upload_file(self, bucket: str, key: str, file_path: str) -> dict:
        """上传本地文件"""
        self.client.upload_file(file_path, bucket, key)
        
        # 获取对象信息
        response = self.client.head_object(Bucket=bucket, Key=key)
        
        return {
            "bucket": bucket,
            "key": key,
            "size": response.get('ContentLength', 0),
            "etag": response.get('ETag', '').strip('"'),
            "last_modified": response.get('LastModified').isoformat() if response.get('LastModified') else None,
        }
    
    def download_file(self, bucket: str, key: str, file_path: str) -> dict:
        """下载到本地"""
        self.client.download_file(bucket, key, file_path)
        
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
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False
    
    def list_objects(self, bucket: str, prefix: str = "") -> list[dict]:
        """列出对象"""
        paginator = self.client.get_paginator('list_objects_v2')
        
        objects = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                objects.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag'].strip('"'),
                })
        
        return objects
    
    def delete_object(self, bucket: str, key: str) -> bool:
        """删除对象"""
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
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
