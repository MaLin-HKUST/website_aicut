import argparse

from common import (
    assert_file_exists,
    get_case_dir,
    get_finalize_original_result_path,
    get_preview_result_path,
    load_config,
    load_json,
    save_json,
)
from src.finalize_processor import OutputMode, process_finalize


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 03: finalize(original) 联调测试")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    task_id = config["task_id"]
    case_dir = get_case_dir(task_id)
    preview_result = load_json(get_preview_result_path(task_id))

    original_video_path = assert_file_exists(config["original_video_path"], "测试输入视频")
    edited_delay_cuts_path = assert_file_exists(
        preview_result["edited_delay_cuts_path"], "preview edited_delay_cuts"
    )
    pause_cuts_on_original_path = assert_file_exists(
        preview_result["pause_cuts_on_original_path"], "preview pause_cuts_on_original"
    )

    result = process_finalize(
        task_id=task_id,
        original_video_path=str(original_video_path),
        edited_delay_cuts_path=str(edited_delay_cuts_path),
        pause_cuts_on_original_path=str(pause_cuts_on_original_path),
        output_mode=OutputMode.ORIGINAL,
        output_dir=str(case_dir / "final_original"),
    )

    save_json(get_finalize_original_result_path(task_id), result)

    print("finalize(original) 完成")
    print(f"结果文件: {get_finalize_original_result_path(task_id)}")
    print(f"最终视频: {result['final_video_path']}")


if __name__ == "__main__":
    main()
