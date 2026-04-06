import argparse
from pathlib import Path

from common import (
    assert_file_exists,
    get_analyze_result_path,
    get_case_dir,
    load_config,
    save_json,
)
from src.analyze_processor import process_analyze


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 01: analyze 联调测试")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    task_id = config["task_id"]
    case_dir = get_case_dir(task_id)

    video_path = assert_file_exists(config["original_video_path"], "测试输入视频")
    reference_path = assert_file_exists(config["reference_text_path"], "测试标准文案")

    result = process_analyze(
        task_id=task_id,
        original_video_path=str(video_path),
        reference_text_path=str(reference_path),
        output_dir=str(case_dir / "analyze"),
    )

    save_json(get_analyze_result_path(task_id), result)

    print("analyze 完成")
    print(f"结果文件: {get_analyze_result_path(task_id)}")
    print(f"script 预览: {result.get('script', '')[:120]}")


if __name__ == "__main__":
    main()
