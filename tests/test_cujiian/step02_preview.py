import argparse
from pathlib import Path

from common import (
    assert_file_exists,
    get_analyze_result_path,
    get_case_dir,
    get_preview_result_path,
    load_config,
    load_json,
    save_json,
)
from src.preview_processor import process_preview


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 02: preview 联调测试")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    task_id = config["task_id"]
    case_dir = get_case_dir(task_id)

    analyze_result = load_json(get_analyze_result_path(task_id))
    artifacts = analyze_result["artifacts"]

    original_script = analyze_result.get("script") or ""
    edited_script = config["edited_script"]

    asr_result_path = assert_file_exists(artifacts["asr_result_path"], "analyze ASR 结果")
    original_video_path = assert_file_exists(config["original_video_path"], "测试输入视频")

    result = process_preview(
        task_id=task_id,
        edited_script=edited_script,
        original_script=original_script,
        asr_result_path=str(asr_result_path),
        original_video_path=str(original_video_path),
        output_dir=str(case_dir / "preview"),
        edit_id="manual-preview-001",
    )

    save_json(get_preview_result_path(task_id), result)

    print("preview 完成")
    print(f"结果文件: {get_preview_result_path(task_id)}")
    print(f"audio_b: {result['audio_b_path']}")
    print("请手动试听 audio_b，确认内容和节奏是否正确。")


if __name__ == "__main__":
    main()
