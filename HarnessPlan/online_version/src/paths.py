"""
路径配置模块

统一管理项目路径，确保在容器内使用绝对路径。
"""

from pathlib import Path

# 根目录配置
AI_CUT_ROOT = Path("/app/aicut2602")
WEBSITE_ROOT = Path("/app/website_aicut")

# 在线版本目录
ONLINE_VERSION_DIR = AI_CUT_ROOT / "libs" / "cut_breakpoints" / "online_version"
SRC_DIR = ONLINE_VERSION_DIR / "src"

# 工作目录配置（Worker 使用）
WORK_BASE_DIR = Path("/data/smart-cut")

# 算法脚本路径
RUN_RAW_CUT = AI_CUT_ROOT / "libs" / "cut_breakpoints" / "src" / "run_raw_cut.py"

# TOS 存储路径配置
TOS_CUJIAN_INPUT_DATA_PREFIX = "cujian_input_data"


def get_task_work_dir(task_id: str) -> Path:
    """获取任务工作目录"""
    return WORK_BASE_DIR / task_id


def get_task_input_dir(task_id: str) -> Path:
    """获取任务输入目录"""
    return get_task_work_dir(task_id) / "input"


def get_task_analyze_dir(task_id: str) -> Path:
    """获取任务分析阶段目录"""
    return get_task_work_dir(task_id) / "analyze"


def get_task_preview_dir(task_id: str) -> Path:
    """获取任务预览阶段目录"""
    return get_task_work_dir(task_id) / "preview"


def get_task_final_dir(task_id: str) -> Path:
    """获取任务最终阶段目录"""
    return get_task_work_dir(task_id) / "final"


def ensure_task_dirs(task_id: str) -> dict:
    """
    确保任务所有目录存在
    
    Returns:
        包含所有目录路径的字典
    """
    dirs = {
        "work": get_task_work_dir(task_id),
        "input": get_task_input_dir(task_id),
        "analyze": get_task_analyze_dir(task_id),
        "preview": get_task_preview_dir(task_id),
        "final": get_task_final_dir(task_id),
    }
    
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    
    return dirs
