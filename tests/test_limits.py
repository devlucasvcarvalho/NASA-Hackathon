import base64

from fastapi.testclient import TestClient

from app.main import app


def test_input_limits(monkeypatch):
    with TestClient(app) as c:
        assert c.post("/api/diagnose", json={"text": ""}).status_code == 422
        assert c.post("/api/diagnose", json={"text": "x" * 4001}).status_code == 422
        assert c.post("/api/chat", json={"message": "y" * 2001}).status_code == 422
        assert c.post("/api/chat", json={"message": ""}).status_code == 422

        assert c.post("/api/diagnose", json={"text": "ferida", "image": "http://evil/x.png"}).status_code == 422
        assert c.post("/api/diagnose", json={"text": "ferida", "image": "data:text/html;base64,AAAA"}).status_code == 422

        tiny = "data:image/png;base64," + base64.b64encode(b"\x89PNG" + b"0" * 100).decode()
        assert c.post("/api/diagnose", json={"text": "ferida no braço", "image": tiny}).status_code == 200

        monkeypatch.setenv("MAX_IMAGE_MB", "0.0001")  # ~100 bytes
        big = "data:image/png;base64," + base64.b64encode(b"0" * 5000).decode()
        assert c.post("/api/diagnose", json={"text": "ferida", "image": big}).status_code == 413
