from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "ai-code-reviewer"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_languages():
    response = client.get("/languages")
    assert response.status_code == 200
    assert "python" in response.json()["languages"]


def test_review_structure():
    response = client.post("/review", json={
        "code": "print('hello')",
        "language": "python"
    })
    assert response.status_code == 200
    data = response.json()
    assert "language" in data
    assert "analysis" in data
    assert "timestamp" in data
def test_models():
    response = client.get("/models")
    assert response.status_code == 200
    assert "models" in response.json()


def test_review_with_model():
    response = client.post("/review", json={
        "code": "print('hello')",
        "language": "python",
        "model": "llama3.2"
    })
    assert response.status_code == 200
    assert response.json()["model"] == "llama3.2"