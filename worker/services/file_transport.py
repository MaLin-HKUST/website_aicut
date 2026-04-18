"""Gateway-owned file transport for Smart Cut tasks.

The gateway is responsible for all TOS transfers. Algorithm execution only
reads and writes local files inside the shared work directory.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx


class GatewayFileTransport:
    """Handle all task file downloads/uploads for the worker gateway."""

    def __init__(self, tos_service: object, workspace: str, bucket: str | None = None):
        self.tos_service = tos_service
        self.workspace = Path(workspace)
        self.bucket = bucket or os.environ.get("TOS_BUCKET", "smart-cut")

    async def download_input(self, source: str, local_path: Path) -> Path:
        """Download one input into the shared work directory."""
        return await asyncio.to_thread(self.download_input_sync, source, local_path)

    def download_input_sync(self, source: str, local_path: Path) -> Path:
        """Synchronous download entry for processors that stay sync."""
        local_path.parent.mkdir(parents=True, exist_ok=True)

        if os.path.exists(source):
            shutil.copy2(source, local_path)
            return local_path

        parsed = urlparse(source)
        if parsed.scheme == "fake":
            self._download_from_fake_url(source, local_path)
            return local_path

        if parsed.scheme in {"http", "https"}:
            self._download_from_http_url_sync(source, local_path)
            return local_path

        self._download_from_tos_key(source, local_path)
        return local_path

    async def upload_output(self, local_path: Path, key: str) -> str:
        """Upload one output from the shared work directory to TOS."""
        return await asyncio.to_thread(self.upload_output_sync, local_path, key)

    def upload_output_sync(self, local_path: Path, key: str) -> str:
        """Synchronous upload entry for processors that stay sync."""
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        self._upload_to_tos(local_path, key)
        return key

    async def upload_directory(self, local_dir: Path, key_prefix: str) -> list[str]:
        """Upload a directory tree to TOS and return uploaded keys."""
        uploaded_keys: list[str] = []
        for file_path in sorted(local_dir.rglob("*")):
            if not file_path.is_file():
                continue
            relative_path = file_path.relative_to(local_dir)
            key = f"{key_prefix}/{relative_path.as_posix()}"
            await self.upload_output(file_path, key)
            uploaded_keys.append(key)
        return uploaded_keys

    def task_dir(self, task_id: str) -> Path:
        return self.workspace / task_id

    def input_dir(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "input"

    def stage_dir(self, task_id: str, stage: str, suffix: Optional[str] = None) -> Path:
        stage_dir = self.task_dir(task_id) / stage
        if suffix:
            stage_dir = stage_dir / suffix
        return stage_dir

    def _download_from_fake_url(self, source: str, local_path: Path) -> None:
        parsed = urlparse(source)
        query = parse_qs(parsed.query)
        local_paths = query.get("local_path", [])
        if local_paths:
            fake_path = Path(local_paths[0])
            if not fake_path.exists():
                raise FileNotFoundError(f"Fake TOS object not found: {fake_path}")
            shutil.copy2(fake_path, local_path)
            return

        path_parts = parsed.path.lstrip("/").split("/", 2)
        if len(path_parts) < 3 or path_parts[0] != "tos":
            raise ValueError(f"Unsupported fake TOS URL: {source}")

        bucket = path_parts[1]
        key = path_parts[2]
        self._download_from_tos_key(key, local_path, bucket=bucket)

    async def _download_from_http_url(self, source: str, local_path: Path) -> None:
        async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
            async with client.stream("GET", source) as response:
                response.raise_for_status()
                with local_path.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            handle.write(chunk)

    def _download_from_http_url_sync(self, source: str, local_path: Path) -> None:
        with httpx.Client(follow_redirects=True, timeout=300.0) as client:
            with client.stream("GET", source) as response:
                response.raise_for_status()
                with local_path.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        if chunk:
                            handle.write(chunk)

    def _download_from_tos_key(self, key: str, local_path: Path, *, bucket: Optional[str] = None) -> None:
        if not self.tos_service or not hasattr(self.tos_service, "download_file"):
            raise RuntimeError("TOS service is not available for download")

        result = self.tos_service.download_file(
            bucket=bucket or self.bucket,
            key=key,
            file_path=str(local_path),
        )
        if not result.success:
            raise RuntimeError(f"Failed to download {key}: {result.error}")

    def _upload_to_tos(self, local_path: Path, key: str) -> None:
        if not self.tos_service or not hasattr(self.tos_service, "upload_file"):
            raise RuntimeError("TOS service is not available for upload")

        result = self.tos_service.upload_file(
            bucket=self.bucket,
            key=key,
            file_path=str(local_path),
        )
        if not result.success:
            raise RuntimeError(f"Failed to upload {key}: {result.error}")
