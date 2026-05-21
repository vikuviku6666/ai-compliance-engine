import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.graph.neo4j_client import get_driver
from app.rag.embedder import create_embedding
from app.services.roadmap_service import RoadmapService
from sqlalchemy import text

client = TestClient(app)


def test_postgres_connection():
    """Verify PostgreSQL and pgvector database connection and table integrity"""
    db = SessionLocal()
    try:
        # Check standard relational connection
        res = db.execute(text("SELECT 1")).fetchone()
        assert res[0] == 1
        
        # Check that knowledge_chunks table exists
        chunk_count = db.execute(text("SELECT count(*) FROM knowledge_chunks")).fetchone()
        assert isinstance(chunk_count[0], int)
    finally:
        db.close()


def test_neo4j_connection_and_traversal():
    """Verify Neo4j driver connection and graph traversal logic for seed KYC Analyst"""
    # Check graph connection
    neo4j_driver = get_driver()
    with neo4j_driver.session() as session:
        res = session.run("RETURN 1").single()
        assert res[0] == 1
        
    # Check that traversal for "KYC Analyst" returns the correct compliance chain
    paths = RoadmapService.traverse_compliance_path("KYC Analyst")
    assert len(paths) > 0
    
    cdd_path = next((p for p in paths if "CDD" in p["training"] and p["responsibility"] == "Customer Onboarding"), None)
    assert cdd_path is not None
    assert cdd_path["responsibility"] == "Customer Onboarding"
    assert cdd_path["risk"] in ("Identity Fraud", "Impersonation Risk")
    assert cdd_path["control"] == "Customer Due Diligence (CDD)"
    assert cdd_path["regulation"] == "Article 22"


def test_embedding_generation():
    """Verify Sentence Transformers embedding generation output dimensions (1024)"""
    vector = create_embedding("Test compliance regulation text")
    assert len(vector) == 1024


def test_health_check_endpoint():
    """Verify FastAPI /health endpoint returns successfully with active database handles"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["postgres"] == "connected"
    assert data["neo4j"] == "connected"


def test_generate_training_endpoint_e2e():
    """Verify deterministic /generate-training roadmap response matches schema exactly"""
    response = client.post("/generate-training", json={"role": "KYC Analyst"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["role"] == "KYC Analyst"
    
    # Check roadmap structure
    roadmap = data["roadmap"]
    assert "Q1" in roadmap
    assert "Q2" in roadmap
    assert "Q3" in roadmap
    assert "Q4" in roadmap
    assert "CDD Fundamentals" in roadmap["Q4"]
    
    # Check details mapping and quiz / simulation inclusions
    details = data["details"]
    assert len(details) > 0
    detail = next((d for d in details if d["training"] == "CDD Fundamentals"), None)
    assert detail is not None
    assert detail["responsibility"] == "Customer Onboarding"
    assert detail["risk"] == "Identity Fraud"
    assert detail["control"] == "CDD"
    assert detail["regulation"] == "Recital 40"
    assert "evidence" in detail
    assert "summary" in detail
    
    # Check generated quiz schema
    quiz = detail["quiz"]
    assert len(quiz) == 3
    assert "question" in quiz[0]
    assert "choices" in quiz[0]
    assert "answer" in quiz[0]
    
    # Check generated simulation schema
    sim = detail["simulation"]
    assert "scenario_title" in sim
    assert "background" in sim
    assert "challenge" in sim
    assert len(sim["options"]) >= 2


def test_quiz_generation_endpoint():
    """Verify that targeting quiz generation directly returns compliant response"""
    response = client.post("/quiz", json={"training": "CDD Fundamentals"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["training"] == "CDD Fundamentals"
    assert data["regulation"] == "Recital 40"
    assert len(data["quiz"]) == 3


def test_simulation_generation_endpoint():
    """Verify that targeting simulation generation directly returns compliant response"""
    response = client.post("/simulation", json={"training": "CDD Fundamentals"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["training"] == "CDD Fundamentals"
    assert data["role"] == "KYC Analyst"
    assert "simulation" in data
    assert "scenario_title" in data["simulation"]


def test_explainability_endpoint():
    """Verify explainability compliance trace returns traversed graph mapping paths"""
    # 1. Test query by role
    response_role = client.get("/explainability?role=KYC Analyst")
    assert response_role.status_code == 200
    data_role = response_role.json()
    assert data_role["search_parameter"] == "role"
    assert data_role["paths_count"] > 0
    
    responsibilities = [p["responsibility"] for p in data_role["paths"]]
    assert "Customer Onboarding" in responsibilities
    
    # 2. Test query by training
    response_train = client.get("/explainability?training=CDD Fundamentals")
    assert response_train.status_code == 200
    data_train = response_train.json()
    assert data_train["search_parameter"] == "training"
    assert data_train["paths_count"] > 0
    
    roles = [p["role"] for p in data_train["paths"]]
    assert "KYC Analyst" in roles


def test_compliance_analyst_generation():
    """Verify that Compliance Analyst produces deterministic roadmap mapping to all 4 quarters"""
    response = client.post("/generate-training", json={"role": "Compliance Analyst"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["role"] == "Compliance Analyst"
    
    roadmap = data["roadmap"]
    assert "Compliance Analyst Compliance Fundamentals (Article 13)" in roadmap["Q1"]
    assert "AML Risk & Control Assessment (Article 14)" in roadmap["Q2"]
    assert "Enhanced Due Diligence and PEP Auditing (Article 18)" in roadmap["Q3"]
    assert "Reporting Suspicious Operations (Article 55)" in roadmap["Q4"]
    
    details = data["details"]
    assert len(details) == 4
    assert details[0]["training"] == "Compliance Analyst Compliance Fundamentals (Article 13)"
    assert details[0]["regulation"] == "Article 13"
    assert "identify the customer and verify the customer's identity" in details[0]["evidence"]


def test_workflow_run_endpoint_deterministic():
    """Verify that POST /workflow/run uses the Neo4j compliance graph to build 4-quarter modules deterministically"""
    response = client.post("/workflow/run", json={"uploaded_text": "Compliance Analyst role"})
    assert response.status_code == 200
    
    data = response.json()
    assert "training_plan_id" in data
    assert data["role_data"]["role"] == "Compliance Analyst"
    
    recs = data["recommendations"]
    assert len(recs) == 4
    
    # Assert that all 4 quarters have exactly 1 module populated
    assert recs[0]["quarter"] == "Q1 Foundation"
    assert recs[0]["module"] == "Compliance Analyst Compliance Fundamentals (Article 13)"
    assert recs[1]["quarter"] == "Q2 Application"
    assert recs[1]["module"] == "AML Risk & Control Assessment (Article 14)"
    assert recs[2]["quarter"] == "Q3 Deepening"
    assert recs[2]["module"] == "Enhanced Due Diligence and PEP Auditing (Article 18)"
    assert recs[3]["quarter"] == "Q4 Embedding"
    assert recs[3]["module"] == "Reporting Suspicious Operations (Article 55)"


