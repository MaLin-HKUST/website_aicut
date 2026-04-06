from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app


class FakeTTSClient:
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
    monkeypatch.setattr("app.main.MinimaxTTSClient", lambda: FakeTTSClient())

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
