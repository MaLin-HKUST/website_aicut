from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.tts import MinimaxConfigError, MinimaxTTSClient


class FakeTTSClient:
    def __init__(self, voice_name: str | None = None):
        self.voice_name = voice_name

    def synthesize(self, text: str):
        return SimpleNamespace(
            audio_bytes=b"fake-audio",
            mime_type="audio/mpeg",
            file_name="tts-demo.mp3",
            usage_characters=30,
        )


def test_tts_requires_auth():
    client = TestClient(app)

    response = client.post("/user/tts/generate", json={"text": "hello world"})

    assert response.status_code == 401


def test_tts_returns_audio_and_usage(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="qa_user", role="user")
    monkeypatch.setattr("app.main.MinimaxTTSClient", lambda voice_name=None: FakeTTSClient(voice_name=voice_name))

    client = TestClient(app)
    response = client.post("/user/tts/generate", json={"text": "123456789012345678901234567890"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["mime_type"] == "audio/mpeg"
    assert payload["file_name"] == "tts-demo.mp3"
    assert payload["usage_credits"] == 30
    assert payload["usage_characters"] == 30
    assert payload["audio_base64"]


def test_tts_passes_selected_voice_name(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="qa_user", role="user")
    created_clients = []

    def fake_client_factory(voice_name=None):
        client = FakeTTSClient(voice_name=voice_name)
        created_clients.append(client)
        return client

    monkeypatch.setattr("app.main.MinimaxTTSClient", fake_client_factory)

    client = TestClient(app)
    response = client.post(
        "/user/tts/generate",
        json={"text": "123456789012345678901234567890", "voice_name": "日标住建-凯迪"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert created_clients[0].voice_name == "日标住建-凯迪"


def test_tts_client_resolves_kdt_voice_name(monkeypatch):
    monkeypatch.setenv("MINIMAX_AUDIO_API_KEY", "test-key")
    monkeypatch.delenv("MINIMAX_TTS_VOICE_ID", raising=False)

    client = MinimaxTTSClient(voice_name="日标住建-小唐")

    assert client._voice_id == "moss_audio_8351c599-5682-11f1-ba6a-025474e1e406"


def test_tts_client_rejects_unknown_voice_name(monkeypatch):
    monkeypatch.setenv("MINIMAX_AUDIO_API_KEY", "test-key")
    monkeypatch.delenv("MINIMAX_TTS_VOICE_ID", raising=False)

    try:
        MinimaxTTSClient(voice_name="未知音色")
    except MinimaxConfigError as exc:
        assert "Unsupported TTS voice_name" in str(exc)
    else:
        raise AssertionError("expected unknown voice_name to fail")
