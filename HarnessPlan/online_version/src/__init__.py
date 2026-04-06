"""
在线版智能剪口播模块

这是一个在现有 aicut2602 算法库之上的在线封装层，
用于支持 website_aicut 的三阶段任务流（analyze -> preview -> finalize）。

规格来源：doc/cujian_plan_cx2.md
"""

__version__ = "0.1.0"

# 路径配置
from .paths import (
    AI_CUT_ROOT,
    WEBSITE_ROOT,
    ONLINE_VERSION_DIR,
    WORK_BASE_DIR,
    RUN_RAW_CUT,
    get_task_work_dir,
    get_task_input_dir,
    get_task_analyze_dir,
    get_task_preview_dir,
    get_task_final_dir,
    ensure_task_dirs,
)

# 脚本格式转换
from .script_formatter import (
    script_to_delete_ranges,
    script_to_html,
    html_to_script,
    apply_delete_ranges,
    validate_script_format,
    extract_visible_text,
    get_delete_ranges_diff,
)

# 音频 B 生成
from .generate_audio_b import (
    generate_audio_b,
    generate_audio_b_with_cuts,
)

# 暂停映射
from .pause_mapping import (
    map_pauses_to_original_seconds,
    dump_pause_cuts_for_direct_cutter,
    load_pause_cuts_from_audio_a,
    map_pauses_from_audio_a_file,
)

# 最终视频切割
from .final_video_cutter import (
    OnlineFinalVideoCutter,
    calculate_output_bitrate,
    cut_final_video,
)

# Analyze 处理器
from .analyze_processor import (
    process_analyze,
    analyze_pipeline,
    get_delete_ranges_from_script,
)

# Preview 处理器
from .preview_processor import (
    process_preview,
)

# Finalize 处理器
from .finalize_processor import (
    process_finalize,
    finalize_pipeline,
    OutputMode,
)

# GroundTruth 记录
from .groundtruth_recorder import (
    record_groundtruth,
    build_groundtruth_tos_path,
    upload_groundtruth,
    create_groundtruth_pipeline,
)

# 数据模型
from .models import (
    TaskStatus,
    UploadStatus,
    OutputMode as OutputModeEnum,
    SmartCutTaskMixin,
    SmartCutEditMixin,
    SMART_CUT_TASK_SQL,
    SMART_CUT_EDIT_SQL,
)

__all__ = [
    # 版本
    "__version__",
    
    # 路径
    "AI_CUT_ROOT",
    "WEBSITE_ROOT",
    "ONLINE_VERSION_DIR",
    "WORK_BASE_DIR",
    "RUN_RAW_CUT",
    "get_task_work_dir",
    "get_task_input_dir",
    "get_task_analyze_dir",
    "get_task_preview_dir",
    "get_task_final_dir",
    "ensure_task_dirs",
    
    # 脚本格式
    "script_to_delete_ranges",
    "script_to_html",
    "html_to_script",
    "apply_delete_ranges",
    "validate_script_format",
    "extract_visible_text",
    "get_delete_ranges_diff",
    
    # 音频
    "generate_audio_b",
    "generate_audio_b_with_cuts",
    
    # 暂停映射
    "map_pauses_to_original_seconds",
    "dump_pause_cuts_for_direct_cutter",
    "load_pause_cuts_from_audio_a",
    "map_pauses_from_audio_a_file",
    
    # 视频切割
    "OnlineFinalVideoCutter",
    "calculate_output_bitrate",
    "cut_final_video",
    
    # 处理器
    "process_analyze",
    "analyze_pipeline",
    "get_delete_ranges_from_script",
    "process_preview",
    "process_finalize",
    "finalize_pipeline",
    "OutputMode",
    
    # GroundTruth
    "record_groundtruth",
    "build_groundtruth_tos_path",
    "upload_groundtruth",
    "create_groundtruth_pipeline",
    
    # 数据模型
    "TaskStatus",
    "UploadStatus",
    "OutputModeEnum",
    "SmartCutTaskMixin",
    "SmartCutEditMixin",
    "SMART_CUT_TASK_SQL",
    "SMART_CUT_EDIT_SQL",
]
