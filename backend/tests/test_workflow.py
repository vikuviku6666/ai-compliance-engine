import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_plans():
    response = client.get("/workflow/plans")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_upload_text():
    # Test text upload
    files = {"file": ("test.txt", b"KYC Analyst responsible for customer due diligence and identity verification.")}
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    assert "customer due diligence" in response.json()["text"]


def test_workflow_run_and_operations():
    # 1. Run generation
    role_description = "Compliance Officer responsible for transaction monitoring and reporting suspicious activity. Primary risks include money laundering and shell companies."
    response = client.post("/workflow/run", json={"uploaded_text": role_description})
    
    assert response.status_code == 200
    data = response.json()
    assert "training_plan_id" in data
    assert "role_data" in data
    assert "recommendations" in data
    
    plan_id = data["training_plan_id"]
    
    # 2. Get specific plan
    plan_response = client.get(f"/workflow/plan/{plan_id}")
    assert plan_response.status_code == 200
    plan_data = plan_response.json()
    assert plan_data["training_plan_id"] == plan_id
    
    # 3. Evaluate plan
    eval_response = client.get(f"/workflow/plan/{plan_id}/evaluate")
    assert eval_response.status_code == 200
    eval_data = eval_response.json()
    assert eval_data["plan_id"] == plan_id
    assert "overall" in eval_data
    assert len(eval_data["dimensions"]) > 0
    
    # 4. Revise plan
    revise_response = client.post(f"/workflow/revise/{plan_id}", json={"feedback": "Add more focus on shell companies in Q2"})
    assert revise_response.status_code == 200
    revised_data = revise_response.json()
    assert revised_data["reviewer_notes"] == "Add more focus on shell companies in Q2"
    
    # 5. Patch plan status
    patch_response = client.patch(f"/training/plans/{plan_id}", json={"status": "approved", "reviewer_notes": "Approved"})
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "success"
