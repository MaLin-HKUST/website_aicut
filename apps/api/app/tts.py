import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


KDT_TTS_VOICE_IDS = {
    "康迪": "moss_audio_623373aa-dd87-11f0-9536-6699b2fade72",
    "日标住建-小唐": "moss_audio_8351c599-5682-11f1-ba6a-025474e1e406",
    "日标住建-凯迪": "moss_audio_18625238-5719-11f1-981b-8a143315d498",
}


class MinimaxTTSError(Exception):
    pass


class MinimaxAPIError(MinimaxTTSError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class MinimaxConfigError(MinimaxTTSError):
    pass


class MinimaxTimeoutError(MinimaxTTSError):
    pass


@dataclass
class TTSSynthesisResult:
    audio_bytes: bytes
    mime_type: str
    file_name: str
    usage_characters: int


class MinimaxTTSClient:
    def __init__(
        self,
        api_key: str | None = None,
        group_id: str | None = None,
        voice_name: str | None = None,
        voice_id: str | None = None,
    ):
        self._api_key = api_key or os.getenv("MINIMAX_AUDIO_API_KEY")
        self._group_id = group_id or os.getenv("MINIMAX_AUDIO_GROUP_ID")
        self._voice_name = str(voice_name or "").strip() or None
        self._voice_id = self._resolve_voice_id(voice_id)
        self._base_url = "https://api.minimax.io"

        if not self._api_key:
            raise MinimaxConfigError("MINIMAX_AUDIO_API_KEY is required")
        if not self._voice_id:
            raise MinimaxConfigError("MINIMAX_TTS_VOICE_ID is required")

    def _resolve_voice_id(self, voice_id: str | None) -> str | None:
        if voice_id:
            return voice_id
        if self._voice_name:
            resolved_voice_id = KDT_TTS_VOICE_IDS.get(self._voice_name)
            if not resolved_voice_id:
                allowed = ", ".join(KDT_TTS_VOICE_IDS)
                raise MinimaxConfigError(f"Unsupported TTS voice_name '{self._voice_name}'. Allowed: {allowed}")
            return resolved_voice_id
        return os.getenv("MINIMAX_TTS_VOICE_ID")

    def synthesize(self, text: str) -> TTSSynthesisResult:
        if not text.strip():
            raise MinimaxConfigError("Text is required")
        if len(text) >= 10_000:
            raise MinimaxConfigError(f"Text exceeds 10,000 characters (got {len(text)})")

        payload = {
            "model": "speech-2.8-hd",
            "text": text,
            "stream": False,
            "output_format": "hex",
            "voice_setting": {
                "voice_id": self._voice_id,
                "speed": 1,
                "vol": 1,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }

        data = self._post_synthesize(payload)
        audio_hex = data.get("data", {}).get("audio")
        if not audio_hex:
            raise MinimaxAPIError("MiniMax response did not contain audio data")

        extra_info = data.get("extra_info", {}) if isinstance(data, dict) else {}
        audio_format = str(extra_info.get("audio_format") or "mp3").lower()
        usage_characters = int(extra_info.get("usage_characters") or len(text))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        return TTSSynthesisResult(
            audio_bytes=bytes.fromhex(audio_hex),
            mime_type=_mime_type_for_format(audio_format),
            file_name=f"tts-{timestamp}.{audio_format}",
            usage_characters=usage_characters,
        )

    @retry(
        retry=retry_if_exception_type((MinimaxAPIError, MinimaxTimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _post_synthesize(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/v1/t2a_v2"
        if self._group_id:
            url = f"{url}?GroupId={self._group_id}"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
        except requests.exceptions.Timeout as exc:
            raise MinimaxTimeoutError("TTS synthesis request timed out") from exc
        except requests.exceptions.RequestException as exc:
            raise MinimaxAPIError(f"TTS synthesis request failed: {exc}") from exc

        if response.status_code != 200:
            raise MinimaxAPIError(
                message=f"TTS synthesis failed: {response.text}",
                status_code=response.status_code,
            )

        data = response.json()
        base_resp = data.get("base_resp") if isinstance(data, dict) else None
        if base_resp and base_resp.get("status_code"):
            raise MinimaxAPIError(
                message=f"TTS synthesis failed: {base_resp.get('status_msg', 'Unknown error')} ({base_resp.get('status_code')})",
                status_code=response.status_code,
            )
        return data


def _mime_type_for_format(audio_format: str) -> str:
    if audio_format == "wav":
        return "audio/wav"
    if audio_format == "flac":
        return "audio/flac"
    return "audio/mpeg"
