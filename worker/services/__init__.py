"""Worker Services - Worker 服务模块

提供服务实现：
- file_transport: Gateway 统一文件下载/上传
- job_contract: Gateway 与算法容器共享目录与 manifest 协议
- groundtruth_service: F22 - GroundTruth 生成和上传服务
"""

from worker.services.file_transport import GatewayFileTransport
from worker.services.job_contract import DEFAULT_WORKER_JOBS_DIR, SmartCutJobContract
from worker.services.groundtruth_service import (
    GroundTruthRecorder,
    GroundTruthService,
    create_groundtruth_service,
)


__all__ = [
    "DEFAULT_WORKER_JOBS_DIR",
    "GatewayFileTransport",
    "SmartCutJobContract",
    "GroundTruthRecorder",
    "GroundTruthService",
    "create_groundtruth_service",
]
