import argparse
from pathlib import Path

from common import (
    assert_file_exists,
    get_analyze_result_path,
    get_case_dir,
    get_groundtruth_result_path,
    load_config,
    load_json,
    real_download,
    real_upload,
    save_json,
)
from src.groundtruth_recorder import create_groundtruth_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 05: groundtruth 联调测试")
    parser.add_argument("--config", required=True, help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    task_id = config["task_id"]
    case_dir = get_case_dir(task_id)
    analyze_result = load_json(get_analyze_result_path(task_id))

    artifacts = analyze_result["artifacts"]
    asr_result_path = assert_file_exists(artifacts["asr_result_path"], "analyze ASR 结果")
    original_video_path = assert_file_exists(config["original_video_path"], "测试输入视频")

    # 上传 ASR 到真实 TOS（原视频假设已在 TOS，这里只记录路径）
    asr_result_url = real_upload(str(asr_result_path), f"smart-cut/{task_id}/analyze/asr_result.json")
    original_video_tos_key = f"smart-cut/{task_id}/input/source_video{Path(original_video_path).suffix}"
    original_video_url = f"https://autocut-malin.tos-cn-shanghai.volces.com/{original_video_tos_key}"

    result = create_groundtruth_pipeline(
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

    save_json(get_groundtruth_result_path(task_id), result)

    print("groundtruth 完成")
    print(f"结果文件: {get_groundtruth_result_path(task_id)}")
    print(f"groundtruth 前缀: {result.get('groundtruth_tos_key')}")


if __name__ == "__main__":
    main()
