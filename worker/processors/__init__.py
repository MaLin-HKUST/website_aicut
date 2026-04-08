"""Worker Processors - SmartCut Worker 处理器模块

包含所有任务处理器实现：
- BaseStageProcessor: 阶段处理器基类
- AnalyzeProcessor: F16 - 分析阶段处理器
- PreviewProcessor: F18 - 预览阶段处理器
- FinalizeProcessor: F20, F21 - 最终生成处理器（含视频归一化）
"""

from worker.processors.base_stage_processor import BaseStageProcessor
from worker.processors.analyze_processor import AnalyzeProcessor
from worker.processors.preview_processor import PreviewProcessor
from worker.processors.finalize_processor import FinalizeProcessor


__all__ = [
    "BaseStageProcessor",
    "AnalyzeProcessor",
    "PreviewProcessor",
    "FinalizeProcessor",
]
