import asyncio
from pathlib import Path

from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType
from apps.services.tos_service import TOSService
from worker.processors.analyze_processor import AnalyzeProcessor
from worker.services.file_transport import GatewayFileTransport


def test_gateway_file_transport_upload_and_download_with_key(tmp_path: Path) -> None:
    fake_tos = tmp_path / "fake_tos"
    workspace = tmp_path / "workspace"
    tos = TOSService(use_fake=True, fake_base_path=str(fake_tos))
    transport = GatewayFileTransport(tos_service=tos, workspace=str(workspace))

    source_file = tmp_path / "source.txt"
    source_file.write_text("hello gateway", encoding="utf-8")

    uploaded_key = asyncio.run(
        transport.upload_output(source_file, "smart-cut/task-1/input/source.txt")
    )
    assert uploaded_key == "smart-cut/task-1/input/source.txt"

    downloaded_path = workspace / "task-1" / "input" / "copied.txt"
    asyncio.run(
        transport.download_input("smart-cut/task-1/input/source.txt", downloaded_path)
    )
    assert downloaded_path.read_text(encoding="utf-8") == "hello gateway"


def test_gateway_file_transport_downloads_fake_presigned_url(tmp_path: Path) -> None:
    fake_tos = tmp_path / "fake_tos"
    workspace = tmp_path / "workspace"
    tos = TOSService(use_fake=True, fake_base_path=str(fake_tos))
    transport = GatewayFileTransport(tos_service=tos, workspace=str(workspace))

    source_file = tmp_path / "video.mp4"
    source_file.write_bytes(b"video-bytes")
    tos.upload_file("smart-cut", "smart-cut/task-2/input/source_video.mp4", str(source_file))

    download_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/task-2/input/source_video.mp4",
    ).data["url"]

    downloaded_path = workspace / "task-2" / "input" / "source_video.mp4"
    asyncio.run(transport.download_input(download_url, downloaded_path))
    assert downloaded_path.read_bytes() == b"video-bytes"


def test_analyze_processor_accepts_current_payload_fields(tmp_path: Path) -> None:
    fake_tos = tmp_path / "fake_tos"
    workspace = tmp_path / "workspace"
    tos = TOSService(use_fake=True, fake_base_path=str(fake_tos))

    video_source = tmp_path / "source_video.mp4"
    video_source.write_bytes(b"video")
    text_source = tmp_path / "reference.txt"
    text_source.write_text("reference", encoding="utf-8")

    tos.upload_file("smart-cut", "smart-cut/task-3/input/source_video.mp4", str(video_source))
    tos.upload_file("smart-cut", "smart-cut/task-3/input/reference.txt", str(text_source))

    video_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/task-3/input/source_video.mp4",
    ).data["url"]
    text_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/task-3/input/reference.txt",
    ).data["url"]

    task = SchedulerTask(
        task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
        business_task_id="task-3",
        payload={
            "original_video_tos_key": video_url,
            "reference_text_tos_key": text_url,
        },
    )

    processor = AnalyzeProcessor(tos, str(workspace))
    processor.set_task(task)
    processor.set_work_dir(workspace / "task-3")

    asyncio.run(processor.prepare_input())

    assert (workspace / "task-3" / "input" / "source_video.mp4").read_bytes() == b"video"
    assert (
        workspace / "task-3" / "input" / "reference.txt"
    ).read_text(encoding="utf-8") == "reference"
