"""Worker 模块 - SmartCut Worker 主流程

F15 实现：Worker 设备注册、心跳、任务轮询和执行。

主要组件：
- SmartCutWorker: Worker 主类
- BaseProcessor: 任务处理器基类
- processors: 具体处理器实现

使用示例：
    ```python
    from worker import SmartCutWorker
    
    worker = SmartCutWorker(
        worker_id="worker-001",
        api_base_url="http://localhost:8000",
        tos_service=tos_service,
        workspace="/tmp/worker-workspace",
    )
    
    await worker.run()
    ```
"""

from worker.core import SmartCutWorker
from worker.base_processor import BaseProcessor
from worker.processors import (
    AnalyzeProcessor,
    PreviewProcessor,
    FinalizeProcessor,
)


__all__ = [
    # 主类
    "SmartCutWorker",
    # 处理器基类
    "BaseProcessor",
    # 具体处理器
    "AnalyzeProcessor",
    "PreviewProcessor",
    "FinalizeProcessor",
]
