from __future__ import annotations

from pathlib import Path

from apps.services.tos_service import RealTOSClient


class _FakeHeadResponse:
    content_length = 123
    etag = '"etag-123"'
    last_modified = "2026-04-20T00:00:00Z"


class _FakeTosClient:
    def __init__(self, *_args, **_kwargs):
        self.calls: list[tuple[str, dict]] = []

    def put_object_from_file(self, bucket: str, key: str, file_path: str):
        self.calls.append(
            ("put_object_from_file", {"bucket": bucket, "key": key, "file_path": file_path})
        )

    def upload_file(self, bucket: str, key: str, file_path: str, **kwargs):
        self.calls.append(
            ("upload_file", {"bucket": bucket, "key": key, "file_path": file_path, **kwargs})
        )

    def head_object(self, _bucket: str, _key: str):
        return _FakeHeadResponse()


def test_real_tos_client_uses_single_put_for_small_files(monkeypatch, tmp_path: Path) -> None:
    import tos

    fake_client = _FakeTosClient()
    monkeypatch.setattr(tos, "TosClientV2", lambda *args, **kwargs: fake_client)
    monkeypatch.setenv("TOS_MULTIPART_THRESHOLD_BYTES", "64")

    source = tmp_path / "small.txt"
    source.write_text("small", encoding="utf-8")

    client = RealTOSClient(
        endpoint="tos-cn-shanghai.volces.com",
        region="cn-shanghai",
        access_key="ak",
        secret_key="sk",
    )

    result = client.upload_file("bucket", "path/small.txt", str(source))

    assert fake_client.calls[0][0] == "put_object_from_file"
    assert result["upload_strategy"] == "single_put"


def test_real_tos_client_uses_multipart_for_large_files(monkeypatch, tmp_path: Path) -> None:
    import tos

    fake_client = _FakeTosClient()
    monkeypatch.setattr(tos, "TosClientV2", lambda *args, **kwargs: fake_client)
    monkeypatch.setenv("TOS_MULTIPART_THRESHOLD_BYTES", "8")
    monkeypatch.setenv("TOS_MULTIPART_PART_SIZE_BYTES", "5")
    monkeypatch.setenv("TOS_MULTIPART_TASK_NUM", "3")

    source = tmp_path / "large.bin"
    source.write_bytes(b"0123456789abcdef")

    client = RealTOSClient(
        endpoint="tos-cn-shanghai.volces.com",
        region="cn-shanghai",
        access_key="ak",
        secret_key="sk",
    )

    result = client.upload_file("bucket", "path/large.bin", str(source))

    assert fake_client.calls[0][0] == "upload_file"
    assert fake_client.calls[0][1]["part_size"] == 5
    assert fake_client.calls[0][1]["task_num"] == 3
    assert fake_client.calls[0][1]["enable_checkpoint"] is True
    assert result["upload_strategy"] == "multipart"
