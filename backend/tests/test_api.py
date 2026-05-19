import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_generate_training():
    response = client.post("/generate-training", json={"role": "KYC Analyst"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "KYC Analyst"
    assert len(data["training"]) > 0
    assert data["training"][0]["training"] == "CDD Fundamentals"

