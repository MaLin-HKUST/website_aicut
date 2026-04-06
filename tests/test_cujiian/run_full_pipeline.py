"""
完整 5 步 pipeline 脚本（Daemon 模式适配版）

执行顺序：analyze -> preview -> finalize(original) -> finalize(vertical) -> groundtruth
任务结束后自动清理所有本地用户数据。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/app/aicut2602/libs/cut_breakpoints/online_version/src")))

from common import (
    assert_file_exists,
    get_analyze_result_path,
    get_case_dir,
    get_finalize_original_result_path,
    get_finalize_vertical_result_path,
    get_groundtruth_result_path,
    get_preview_result_path,
    load_config,
    real_download,
    real_upload,
    save_json,
)
from paths import cleanup_task_dirs
from src.analyze_processor import process_analyze
from src.finalize_processor import OutputMode, process_finalize
from src.groundtruth_recorder import create_groundtruth_pipeline
from src.preview_processor import process_preview


def main() -> None:
    parser = argparse.ArgumentParser(description="Cujian 5-Step Full Pipeline")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    task_id = config["task_id"]
    case_dir = get_case_dir(task_id)

    # 每次任务开始前清理旧数据（防止重跑冲突）
    cleanup_task_dirs(task_id)
    for sub in ["analyze", "preview", "final_original", "final_vertical", "groundtruth"]:
        d = case_dir / sub
        if d.exists():
            import shutil
            shutil.rmtree(d)
    for f in [
        get_analyze_result_path(task_id),
        get_preview_result_path(task_id),
        get_finalize_original_result_path(task_id),
        get_finalize_vertical_result_path(task_id),
        get_groundtruth_result_path(task_id),
    ]:
        if f.exists():
            f.unlink()

    try:
        # Step 01: analyze
        video_path = assert_file_exists(config["original_video_path"], "测试输入视频")
        reference_path = assert_file_exists(config["reference_text_path"], "测试标准文案")
        analyze_result = process_analyze(
            task_id=task_id,
            original_video_path=str(video_path),
            reference_text_path=str(reference_path),
            output_dir=str(case_dir / "analyze"),
        )
        save_json(get_analyze_result_path(task_id), analyze_result)
        print("[OK] step01 analyze")

        # Step 02: preview
        artifacts = analyze_result["artifacts"]
        asr_path = assert_file_exists(artifacts["asr_result_path"], "analyze ASR 结果")
        preview_result = process_preview(
            task_id=task_id,
            edited_script=config["edited_script"],
            original_script=analyze_result.get("script") or "",
            asr_result_path=str(asr_path),
            original_video_path=str(video_path),
            output_dir=str(case_dir / "preview"),
            edit_id="manual-preview-001",
        )
        save_json(get_preview_result_path(task_id), preview_result)
        print("[OK] step02 preview")

        # Step 03: finalize_original
        preview_data = preview_result
        original_video = assert_file_exists(config["original_video_path"], "测试输入视频")
        edited_delay_cuts = assert_file_exists(preview_data["edited_delay_cuts_path"], "preview edited_delay_cuts")
        pause_cuts = assert_file_exists(preview_data["pause_cuts_on_original_path"], "preview pause_cuts_on_original")
        finalize_original_result = process_finalize(
            task_id=task_id,
            original_video_path=str(original_video),
            edited_delay_cuts_path=str(edited_delay_cuts),
            pause_cuts_on_original_path=str(pause_cuts),
            output_mode=OutputMode.ORIGINAL,
            output_dir=str(case_dir / "final_original"),
        )
        save_json(get_finalize_original_result_path(task_id), finalize_original_result)
        print("[OK] step03 finalize_original")

        # Step 04: finalize_vertical
        finalize_vertical_result = process_finalize(
            task_id=task_id,
            original_video_path=str(original_video),
            edited_delay_cuts_path=str(edited_delay_cuts),
            pause_cuts_on_original_path=str(pause_cuts),
            output_mode=OutputMode.VERTICAL_1080P,
            output_dir=str(case_dir / "final_vertical"),
        )
        save_json(get_finalize_vertical_result_path(task_id), finalize_vertical_result)
        print("[OK] step04 finalize_vertical")

        # Step 05: groundtruth
        asr_result_path = assert_file_exists(artifacts["asr_result_path"], "analyze ASR 结果")
        asr_result_url = real_upload(str(asr_result_path), f"smart-cut/{task_id}/analyze/asr_result.json")
        original_video_tos_key = f"smart-cut/{task_id}/input/source_video{Path(str(original_video)).suffix}"
        original_video_url = f"https://autocut-malin.tos-cn-shanghai.volces.com/{original_video_tos_key}"

        groundtruth_result = create_groundtruth_pipeline(
            task_id=task_id,
            company=config["company"],
            reference_text=Path(config["reference_text_path"]).read_text(encoding="utf-8"),
            original_video_url=original_video_url,
            original_video_tos_key=original_video_tos_key,
            asr_result_url=asr_result_url,
            analyze_script=analyze_result.get("script") or "",
            edited_script=config["edited_script"],
            work_dir=str(case_dir),
            upload_fn=real_upload,
            download_fn=real_download,
        )
        save_json(get_groundtruth_result_path(task_id), groundtruth_result)
        print("[OK] step05 groundtruth")
        print(f"groundtruth 前缀: {groundtruth_result.get('groundtruth_tos_key')}")

    finally:
        # 任务结束后清理所有本地用户数据（Daemon 模式必需）
        print("[CLEANUP] 清理任务本地数据...")
        cleanup_task_dirs(task_id)
        if case_dir.exists():
            import shutil
            shutil.rmtree(case_dir)
        print("[CLEANUP] 完成")


if __name__ == "__main__":
    main()
