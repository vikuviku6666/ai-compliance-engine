from fastapi import APIRouter, File, UploadFile, HTTPException
import json
import uuid
from datetime import datetime
from app.db.database import SessionLocal
from app.graph.neo4j_client import driver
from app.services.roadmap_service import RoadmapService
from app.services.quiz_service import QuizService
from app.services.simulation_service import SimulationService
from app.models.models import TrainingPlan, TrainingPlanModule
from app.services.generator import TrainingPlanGenerator
from app.services.compliance_engine import build_compliance_training_plan
from sqlalchemy import text

router = APIRouter()


# ==========================================
# LIVE GRAPH & KNOWLEDGE ENDPOINTS
# ==========================================

@router.get("/graph/roles")
def get_roles():
    """Return all roles with their responsibilities and risks — live from Neo4j."""
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
            OPTIONAL MATCH (resp)-[:INTRODUCES]->(risk:Risk)
            RETURN r.name AS role,
                   collect(DISTINCT resp.name) AS responsibilities,
                   collect(DISTINCT risk.name) AS risks
            ORDER BY r.name
        """)
        roles = []
        for record in result:
            roles.append({
                "role":             record["role"],
                "responsibilities": [r for r in record["responsibilities"] if r],
                "risks":            [r for r in record["risks"] if r],
            })
        return {"roles": roles, "count": len(roles)}


@router.get("/graph/role/{role_name}")
def get_role_detail(role_name: str):
    """Return full governance paths for a specific role — live from Neo4j."""
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Role {name: $role})
            MATCH (r)-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
            MATCH (resp)-[:INTRODUCES]->(risk:Risk)
            MATCH (risk)-[:MITIGATED_BY]->(ctrl:Control)
            MATCH (ctrl)-[:REQUIRED_BY]->(reg:Regulation)
            MATCH (ctrl)-[:TRAINED_BY]->(t:Training)
            RETURN DISTINCT
                resp.name  AS responsibility,
                risk.name  AS risk,
                ctrl.name  AS control,
                reg.name   AS regulation,
                t.name     AS training
            ORDER BY reg.name
        """, role=role_name)
        paths = [dict(r) for r in result]
        if not paths:
            raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found in governance graph")
        return {
            "role":  role_name,
            "paths": paths,
            "count": len(paths),
        }


@router.get("/graph/regulations")
def get_regulations():
    """Return all regulation articles/recitals available in the knowledge index — live from PostgreSQL."""
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT DISTINCT section, legal_type, article_num, recital_num,
                   LEFT(content, 200) AS preview
            FROM knowledge_chunks
            WHERE legal_type IN ('article', 'recital')
            ORDER BY legal_type, article_num NULLS LAST, recital_num NULLS LAST
        """)).fetchall()

        return {
            "regulations": [
                {
                    "section":      r.section,
                    "legal_type":   r.legal_type,
                    "article_num":  r.article_num,
                    "recital_num":  r.recital_num,
                    "reference":    (
                        f"Article {r.article_num} — EU AMLR 2024/1624" if r.article_num
                        else f"Recital {r.recital_num} — EU AMLR 2024/1624"
                    ),
                    "preview":      r.preview,
                }
                for r in rows
            ],
            "count": len(rows),
        }
    finally:
        db.close()


@router.post("/graph/suggest-risks")
def suggest_risks(data: dict):
    """Given a list of responsibilities, suggest inherent risks using Neo4j + knowledge index."""
    responsibilities = data.get("responsibilities", [])
    role = data.get("role", "")
    if not responsibilities:
        raise HTTPException(status_code=400, detail="'responsibilities' required")

    suggestions = []
    seen = set()

    with driver.session() as session:
        # 1. Exact match from graph
        for resp in responsibilities:
            result = session.run("""
                MATCH (resp:Responsibility {name: $resp})-[:INTRODUCES]->(risk:Risk)
                RETURN DISTINCT risk.name AS risk
            """, resp=resp)
            for r in result:
                if r["risk"] not in seen:
                    seen.add(r["risk"])
                    suggestions.append({
                        "risk":   r["risk"],
                        "source": "governance_graph",
                        "responsibility": resp,
                    })

        # 2. Fuzzy match — search by role name
        if role:
            result = session.run("""
                MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
                      -[:INTRODUCES]->(risk:Risk)
                WHERE toLower(r.name) CONTAINS toLower($role)
                RETURN DISTINCT risk.name AS risk, resp.name AS responsibility
            """, role=role)
            for r in result:
                if r["risk"] not in seen:
                    seen.add(r["risk"])
                    suggestions.append({
                        "risk":   r["risk"],
                        "source": "governance_graph",
                        "responsibility": r["responsibility"],
                    })

    # 3. RAG fallback for any responsibility not in graph
    graph_covered = {s["responsibility"] for s in suggestions}
    uncovered = [r for r in responsibilities if r not in graph_covered]
    if uncovered:
        from app.rag.knowledge_index import KnowledgeIndexBuilder
        builder = KnowledgeIndexBuilder()
        for resp in uncovered[:3]:
            hits = builder.search(resp + " risk money laundering", limit=2)
            for h in hits:
                if h["legal_type"] in ("article", "recital"):
                    risk_label = f"Compliance risk under {h['section']}"
                    if risk_label not in seen:
                        seen.add(risk_label)
                        suggestions.append({
                            "risk":        risk_label,
                            "source":      "knowledge_index",
                            "regulation":  h["section"],
                            "responsibility": resp,
                        })

    return {
        "responsibilities_queried": responsibilities,
        "suggested_risks": suggestions,
        "count": len(suggestions),
    }


@router.post("/graph/suggest-controls")
def suggest_controls(data: dict):
    """Given risks, return the controls that mitigate them — live from Neo4j."""
    risks = data.get("risks", [])
    if not risks:
        raise HTTPException(status_code=400, detail="'risks' required")

    results = []
    seen = set()
    with driver.session() as session:
        for risk in risks:
            rows = session.run("""
                MATCH (risk:Risk)-[:MITIGATED_BY]->(ctrl:Control)
                      -[:REQUIRED_BY]->(reg:Regulation)
                WHERE toLower(risk.name) CONTAINS toLower($risk)
                   OR toLower($risk) CONTAINS toLower(risk.name)
                RETURN DISTINCT ctrl.name AS control, reg.name AS regulation,
                       risk.name AS matched_risk
            """, risk=risk)
            for r in rows:
                key = (r["control"], r["regulation"])
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "risk":       risk,
                        "matched_risk": r["matched_risk"],
                        "control":    r["control"],
                        "regulation": r["regulation"],
                    })

    return {
        "risks_queried":    risks,
        "controls_found":   results,
        "count":            len(results),
    }



@router.post("/compliance/generate-plan")
def compliance_generate_plan(data: dict):
    """
    PRIMARY ENDPOINT — Core compliance training plan generator.

    Input:
        role            : str          — e.g. "KYC Analyst"
        responsibilities: list[str]    — e.g. ["Customer Onboarding", "PEP Screening"]
        inherent_risks  : list[str]    — e.g. ["Identity Fraud", "Shell Company Laundering"]

    Flow:
        1. Neo4j graph traversal (deterministic governance)
        2. EU AMLR knowledge index regulation lookup per risk
        3. Evidence chain assembly with article/recital citations
        4. LLM generates module descriptions (strictly grounded)
        5. 4-quarter training plan with full explainability trace

    Returns:
        role, plan (4 quarters), roadmap, audit_summary
        Each module carries: article_num, regulation_ref, risk, control,
        evidence, description, explainability_trace
    """
    role = data.get("role", "").strip()
    responsibilities = data.get("responsibilities", [])
    inherent_risks = data.get("inherent_risks", [])
    domain = data.get("domain", "Banking & Payments").strip()

    if not role:
        raise HTTPException(status_code=400, detail="Missing required field: 'role'")
    if not isinstance(responsibilities, list):
        raise HTTPException(status_code=400, detail="'responsibilities' must be a list")
    if not isinstance(inherent_risks, list):
        raise HTTPException(status_code=400, detail="'inherent_risks' must be a list")

    try:
        result = build_compliance_training_plan(
            role=role,
            responsibilities=responsibilities,
            inherent_risks=inherent_risks,
            domain=domain,
        )

        # Persist to database
        plan_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        db = SessionLocal()
        try:
            plan_row = TrainingPlan(
                plan_id=plan_id,
                role=role,
                responsibilities=json.dumps(responsibilities),
                risks=json.dumps(inherent_risks),
                status="draft",
                overall_score=0,
                created_at=created_at,
            )
            db.add(plan_row)

            for idx, mod in enumerate(result["plan"]):
                mod_row = TrainingPlanModule(
                    id=f"{plan_id}_mod_{idx}",
                    plan_id=plan_id,
                    quarter=mod["quarter"],
                    module=mod["module"],
                    role_reference=mod["responsibility"],
                    regulation_reference=mod["regulation_ref"],
                    risk_reference=mod["risk"],
                    competency_reference=mod["competency"],
                    behavioural_outcome=mod["description"],
                )
                db.add(mod_row)

            db.commit()
        except Exception as db_err:
            db.rollback()
            print(f"DB persist error: {db_err}")
        finally:
            db.close()

        result["plan_id"] = plan_id
        result["created_at"] = created_at
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/explainability/{plan_id}")
def compliance_explainability(plan_id: str):
    """
    Return full explainability trace for a generated compliance training plan.

    For each module shows the complete governance chain:
        Role → Responsibility → Risk → Control → Regulation (Article X) → Training
    """
    db = SessionLocal()
    try:
        plan = db.query(TrainingPlan).filter_by(plan_id=plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        modules = db.query(TrainingPlanModule).filter_by(plan_id=plan_id).all()

        try:
            responsibilities = json.loads(plan.responsibilities)
        except Exception:
            responsibilities = [plan.responsibilities]
        try:
            risks = json.loads(plan.risks)
        except Exception:
            risks = [plan.risks]

        traces = []
        for m in modules:
            traces.append({
                "quarter":          m.quarter,
                "training":         m.module,
                "governance_chain": {
                    "role":             plan.role,
                    "responsibility":   m.role_reference,
                    "risk":             m.risk_reference,
                    "control":          "See regulation reference",
                    "regulation_ref":   m.regulation_reference,
                    "competency":       m.competency_reference,
                },
                "behavioural_outcome": m.behavioural_outcome,
            })

        return {
            "plan_id":           plan_id,
            "role":              plan.role,
            "responsibilities":  responsibilities,
            "inherent_risks":    risks,
            "status":            plan.status,
            "created_at":        plan.created_at,
            "module_count":      len(traces),
            "explainability_traces": traces,
            "audit_note": (
                "All training modules are derived from EU AMLR 2024/1624 via deterministic "
                "Neo4j governance graph traversal and vector-based regulation retrieval. "
                "The LLM was used only for description generation, not for governance decisions."
            ),
        }
    finally:
        db.close()


@router.post("/compliance/regulations-for-risks")
def regulations_for_risks(data: dict):
    """
    Given a list of risks (and optional responsibilities), return the EU AMLR
    regulations and article numbers that address each risk.

    Useful for explainability before generating a full plan.
    """
    risks = data.get("risks", [])
    responsibilities = data.get("responsibilities", [])

    if not risks:
        raise HTTPException(status_code=400, detail="Missing required field: 'risks'")

    from app.services.compliance_engine import find_regulations_for_risks
    results = find_regulations_for_risks(
        risks=risks,
        responsibilities=responsibilities,
        limit_per_risk=3,
    )
    return {
        "risks_queried": risks,
        "regulations_found": results,
        "count": len(results),
    }


@router.post("/extract-role")
def extract_role(data: dict):
    """Extract role, responsibilities, and risks from free text — single LLM call only.

    Lightweight endpoint used by the frontend on Generate click.
    Does NOT run plan generation, RAG search, or evaluation.
    Returns { role, responsibilities, risks } immediately after one LLM call.
    """
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text' field.")

    gen = TrainingPlanGenerator()
    role_info = gen.extract_role_info(text)
    return role_info  # { role, responsibilities, risks }


@router.post("/extract-multiple-roles")
def extract_multiple_roles_endpoint(data: dict):
    """Extract multiple roles with responsibilities and risks from raw text (e.g. PDF).

    Returns:
        roles: list[dict] where each dict is { role, responsibilities, inherent_risks }
    """
    text = data.get("text", "").strip()
    domain = data.get("domain", "Banking & Payments").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text' field.")

    gen = TrainingPlanGenerator()
    roles = gen.extract_multiple_roles(text, domain=domain)
    return {"roles": roles}


@router.get("/health")
def health_check():
    """Verify health and connectivity for Neo4j compliance graph and PostgreSQL relational database"""
    postgres_status = "connected"
    neo4j_status = "connected"
    
    # Verify Postgres connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        print(f"Health check PostgreSQL connection error: {e}")
        postgres_status = "disconnected"
        
    # Verify Neo4j connection
    try:
        with driver.session() as session:
            session.run("RETURN 1")
    except Exception as e:
        print(f"Health check Neo4j connection error: {e}")
        neo4j_status = "disconnected"
        
    if postgres_status == "disconnected" or neo4j_status == "disconnected":
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "postgres": postgres_status,
                "neo4j": neo4j_status
            }
        )
        
    return {
        "status": "healthy",
        "postgres": postgres_status,
        "neo4j": neo4j_status
    }


@router.post("/generate-training")
def generate_training(data: dict):
    """Generate deterministic AML training paths and detail modules using compliance graph traversal and legal evidence"""
    role_name = data.get("role")
    if not role_name:
        raise HTTPException(status_code=400, detail="Missing required 'role' key.")
        
    # Traverse Neo4j compliance graph deterministically
    paths = RoadmapService.traverse_compliance_path(role_name)
    if not paths:
        # Graceful fallback to seed Role
        paths = RoadmapService.traverse_compliance_path("KYC Analyst")
        
    roadmap = {
        "Q1": [],
        "Q2": [],
        "Q3": [],
        "Q4": []
    }
    details = []
    
    import re
    def get_reg_num(p):
        reg = p.get("regulation", "")
        numbers = [int(s) for s in re.findall(r'\d+', reg)]
        return numbers[0] if numbers else 999
    paths.sort(key=get_reg_num)
    
    for idx, path in enumerate(paths):
        training_name = path["training"]
        control_name = path["control"]
        regulation_name = path["regulation"]
        responsibility_name = path["responsibility"]
        risk_name = path["risk"]
        
        # Stable deterministic quarterly mapping
        quarter = f"Q{(idx % 4) + 1}"
        roadmap[quarter].append(training_name)
        
        # Retrieve legal text / evidence from PostgreSQL vector storage
        evidence = RoadmapService.get_legal_evidence(regulation_name)
        
        # Strictly factual summary compilation using LLM (temp=0)
        summary = RoadmapService.generate_summary(training_name, control_name, regulation_name, evidence)
        
        # Strictly factual quiz compilation using LLM (temp=0)
        quiz = QuizService.generate_quiz(training_name, regulation_name, evidence)
        
        # Factual simulation design using LLM (temp=0)
        simulation = SimulationService.generate_simulation(
            training_name,
            responsibility_name,
            risk_name,
            control_name,
            regulation_name,
            evidence
        )
        
        details.append({
            "training": training_name,
            "role": role_name,
            "responsibility": responsibility_name,
            "risk": risk_name,
            "control": control_name,
            "regulation": regulation_name,
            "evidence": evidence,
            "summary": summary,
            "quiz": quiz,
            "simulation": simulation
        })
        
    return {
        "role": role_name,
        "roadmap": roadmap,
        "details": details
    }


@router.post("/quiz")
def generate_quiz_endpoint(data: dict):
    """Generate an audit-ready quiz based strictly on the regulation mapped to a targeted course module"""
    training_name = data.get("training")
    if not training_name:
        raise HTTPException(status_code=400, detail="Missing required 'training' key.")
        
    query = """
    MATCH (training:Training {name: $training})
    MATCH (control:Control)-[:TRAINED_BY]->(training)
    MATCH (control)-[:REQUIRED_BY]->(reg:Regulation)
    RETURN DISTINCT reg.name as regulation
    """
    regulation_name = "Recital 40"
    with driver.session() as session:
        res = session.run(query, training=training_name)
        record = res.single()
        if record:
            regulation_name = record["regulation"]
            
    evidence = RoadmapService.get_legal_evidence(regulation_name)
    quiz = QuizService.generate_quiz(training_name, regulation_name, evidence)
    
    return {
        "training": training_name,
        "regulation": regulation_name,
        "quiz": quiz
    }


@router.post("/simulation")
def generate_simulation_endpoint(data: dict):
    """Generate an interactive compliance simulation based strictly on targeted role, risk, control, and regulation details"""
    training_name = data.get("training")
    if not training_name:
        raise HTTPException(status_code=400, detail="Missing required 'training' key.")
        
    query = """
    MATCH (training:Training {name: $training})
    MATCH (control:Control)-[:TRAINED_BY]->(training)
    MATCH (control)-[:REQUIRED_BY]->(reg:Regulation)
    MATCH (risk:Risk)-[:MITIGATED_BY]->(control)
    MATCH (resp:Responsibility)-[:INTRODUCES]->(risk)
    MATCH (role:Role)-[:HAS_RESPONSIBILITY]->(resp)
    RETURN DISTINCT
        role.name as role,
        resp.name as responsibility,
        risk.name as risk,
        control.name as control,
        reg.name as regulation
    """
    
    responsibility_name = "Customer Onboarding"
    risk_name = "Identity Fraud"
    control_name = "CDD"
    regulation_name = "Recital 40"
    role_name = "KYC Analyst"
    
    with driver.session() as session:
        res = session.run(query, training=training_name)
        record = res.single()
        if record:
            responsibility_name = record["responsibility"]
            risk_name = record["risk"]
            control_name = record["control"]
            regulation_name = record["regulation"]
            role_name = record["role"]
            
    evidence = RoadmapService.get_legal_evidence(regulation_name)
    simulation = SimulationService.generate_simulation(
        training_name,
        responsibility_name,
        risk_name,
        control_name,
        regulation_name,
        evidence
    )
    
    return {
        "training": training_name,
        "role": role_name,
        "responsibility": responsibility_name,
        "risk": risk_name,
        "control": control_name,
        "regulation": regulation_name,
        "simulation": simulation
    }


@router.get("/explainability")
def explainability_endpoint(role: str = None, training: str = None):
    """Explain the trace and logic connecting role, responsibility, risk, control, regulation, and training"""
    if not role and not training:
        raise HTTPException(status_code=400, detail="Must provide 'role' or 'training' query parameter.")
        
    paths = []
    if role:
        query = """
        MATCH (r:Role {name: $role})
        MATCH (r)-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
        MATCH (resp)-[:INTRODUCES]->(risk:Risk)
        MATCH (risk)-[:MITIGATED_BY]->(control:Control)
        MATCH (control)-[:REQUIRED_BY]->(reg:Regulation)
        MATCH (control)-[:TRAINED_BY]->(training:Training)
        RETURN DISTINCT
            r.name as role,
            resp.name as responsibility,
            risk.name as risk,
            control.name as control,
            reg.name as regulation,
            training.name as training
        """
        with driver.session() as session:
            res = session.run(query, role=role)
            paths = [dict(r) for r in res]
    else:
        query = """
        MATCH (training:Training {name: $training})
        MATCH (control:Control)-[:TRAINED_BY]->(training)
        MATCH (control)-[:REQUIRED_BY]->(reg:Regulation)
        MATCH (risk:Risk)-[:MITIGATED_BY]->(control)
        MATCH (resp:Responsibility)-[:INTRODUCES]->(risk)
        MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp)
        RETURN DISTINCT
            r.name as role,
            resp.name as responsibility,
            risk.name as risk,
            control.name as control,
            reg.name as regulation,
            training.name as training
        """
        with driver.session() as session:
            res = session.run(query, training=training)
            paths = [dict(r) for r in res]
            
    return {
        "search_parameter": "role" if role else "training",
        "value": role or training,
        "paths_count": len(paths),
        "paths": paths
    }


# ==========================================
# COMPATIBILITY WORKFLOW & GRAPH API ENDPOINTS
# ==========================================

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    """Extract text from uploaded compliance/role files (PDF/TXT)"""
    filename = file.filename or "unknown"
    content = ""
    try:
        if filename.lower().endswith(".pdf"):
            import PyPDF2
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.file.read()))
            pages_text = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            content = "\n".join(pages_text)
        else:
            content = file.file.read().decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
        
    return {"text": content}


@router.post("/workflow/run")
def workflow_run(data: dict):
    """Orchestrates RAG context search and generates a persistent 1-year training plan"""
    uploaded_text = data.get("uploaded_text", "")
    if not uploaded_text.strip():
        raise HTTPException(status_code=400, detail="Missing uploaded_text field.")
        
    gen = TrainingPlanGenerator()
    
    # 1. Extract Role info
    role_info = gen.extract_role_info(uploaded_text)
    role = role_info["role"]
    responsibilities = role_info["responsibilities"]
    risks = role_info["risks"]
    
    # 2. Search RAG context
    rag_context = gen.get_rag_context(responsibilities, risks)
    
    # 3. Generate 1-year plan modules
    recommendations = gen.generate_plan(role, responsibilities, risks, rag_context)
    
    # 4. Evaluate Plan Scorecard
    evaluation = gen.evaluate_plan(role, responsibilities, risks, recommendations)
    overall_score = evaluation.get("overall", 80)
    
    plan_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    db = SessionLocal()
    try:
        plan = TrainingPlan(
            plan_id=plan_id,
            role=role,
            responsibilities=json.dumps(responsibilities),
            risks=json.dumps(risks),
            status="draft",
            overall_score=overall_score,
            created_at=created_at
        )
        db.add(plan)
        
        for i, rec in enumerate(recommendations):
            mod_id = f"{plan_id}_mod_{i}"
            module = TrainingPlanModule(
                id=mod_id,
                plan_id=plan_id,
                quarter=rec.get("quarter") or "Q1 Foundation",
                module=rec.get("module") or "Compliance Activity",
                role_reference=rec.get("role_reference") or "",
                regulation_reference=rec.get("regulation_reference") or "",
                risk_reference=rec.get("risk_reference") or "",
                competency_reference=rec.get("competency_reference") or "Foundational",
                behavioural_outcome=rec.get("behavioural_outcome") or ""
            )
            db.add(module)
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error saving plan: {str(e)}")
    finally:
        db.close()
        
    return {
        "training_plan_id": plan_id,
        "role_data": {
            "role": role,
            "responsibilities": responsibilities,
            "risks": risks
        },
        "recommendations": recommendations
    }


@router.get("/workflow/plans")
def get_plans():
    """Retrieve history of saved compliance training plans"""
    db = SessionLocal()
    try:
        plans = db.query(TrainingPlan).order_by(TrainingPlan.created_at.desc()).all()
        results = []
        for p in plans:
            mod_count = db.query(TrainingPlanModule).filter_by(plan_id=p.plan_id).count()
            results.append({
                "plan_id": p.plan_id,
                "role": p.role,
                "status": p.status,
                "module_count": mod_count,
                "created_at": p.created_at
            })
        return results
    finally:
        db.close()


@router.get("/workflow/plan/{plan_id}")
def get_plan(plan_id: str):
    """Retrieve full details of a specific compliance plan"""
    db = SessionLocal()
    try:
        plan = db.query(TrainingPlan).filter_by(plan_id=plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        modules = db.query(TrainingPlanModule).filter_by(plan_id=plan_id).all()
        
        try:
            responsibilities = json.loads(plan.responsibilities)
        except Exception:
            responsibilities = [plan.responsibilities] if plan.responsibilities else []
            
        try:
            risks = json.loads(plan.risks)
        except Exception:
            risks = [plan.risks] if plan.risks else []
            
        recommendations = [
            {
                "quarter": m.quarter,
                "module": m.module,
                "role_reference": m.role_reference,
                "regulation_reference": m.regulation_reference,
                "risk_reference": m.risk_reference,
                "competency_reference": m.competency_reference,
                "behavioural_outcome": m.behavioural_outcome
            }
            for m in modules
        ]
        
        return {
            "training_plan_id": plan.plan_id,
            "role_data": {
                "role": plan.role,
                "responsibilities": responsibilities,
                "risks": risks
            },
            "recommendations": recommendations,
            "reviewer_notes": plan.reviewer_notes
        }
    finally:
        db.close()


@router.post("/workflow/revise/{plan_id}")
def revise_plan_endpoint(plan_id: str, data: dict):
    """Revise and update an existing plan based on user comments/feedback"""
    feedback = data.get("feedback", "")
    db = SessionLocal()
    try:
        plan = db.query(TrainingPlan).filter_by(plan_id=plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        modules = db.query(TrainingPlanModule).filter_by(plan_id=plan_id).all()
        
        try:
            responsibilities = json.loads(plan.responsibilities)
        except Exception:
            responsibilities = [plan.responsibilities] if plan.responsibilities else []
            
        try:
            risks = json.loads(plan.risks)
        except Exception:
            risks = [plan.risks] if plan.risks else []
            
        current_modules = [
            {
                "quarter": m.quarter,
                "module": m.module,
                "role_reference": m.role_reference,
                "regulation_reference": m.regulation_reference,
                "risk_reference": m.risk_reference,
                "competency_reference": m.competency_reference,
                "behavioural_outcome": m.behavioural_outcome
            }
            for m in modules
        ]
        
        gen = TrainingPlanGenerator()
        revised_modules = gen.revise_plan(
            plan_id,
            plan.role,
            responsibilities,
            risks,
            current_modules,
            feedback
        )
        
        evaluation = gen.evaluate_plan(plan.role, responsibilities, risks, revised_modules)
        overall_score = evaluation.get("overall", 80)
        
        # Clear existing modules
        db.query(TrainingPlanModule).filter_by(plan_id=plan_id).delete()
        
        # Insert revised modules
        for i, rec in enumerate(revised_modules):
            mod_id = f"{plan_id}_mod_revised_{i}"
            module = TrainingPlanModule(
                id=mod_id,
                plan_id=plan_id,
                quarter=rec.get("quarter") or "Q1 Foundation",
                module=rec.get("module") or "Compliance Activity",
                role_reference=rec.get("role_reference") or "",
                regulation_reference=rec.get("regulation_reference") or "",
                risk_reference=rec.get("risk_reference") or "",
                competency_reference=rec.get("competency_reference") or "Foundational",
                behavioural_outcome=rec.get("behavioural_outcome") or ""
            )
            db.add(module)
            
        # Update metadata
        plan.status = "revised"
        plan.overall_score = overall_score
        plan.reviewer_notes = feedback
        
        db.commit()
        
        return {
            "training_plan_id": plan_id,
            "role_data": {
                "role": plan.role,
                "responsibilities": responsibilities,
                "risks": risks
            },
            "recommendations": revised_modules,
            "reviewer_notes": feedback
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error revising plan: {str(e)}")
    finally:
        db.close()


@router.get("/workflow/plan/{plan_id}/evaluate")
def evaluate_plan_endpoint(plan_id: str):
    """Retrieve details for plan quality scorecard"""
    db = SessionLocal()
    try:
        plan = db.query(TrainingPlan).filter_by(plan_id=plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        modules = db.query(TrainingPlanModule).filter_by(plan_id=plan_id).all()
        
        try:
            responsibilities = json.loads(plan.responsibilities)
        except Exception:
            responsibilities = [plan.responsibilities] if plan.responsibilities else []
            
        try:
            risks = json.loads(plan.risks)
        except Exception:
            risks = [plan.risks] if plan.risks else []
            
        current_modules = [
            {
                "quarter": m.quarter,
                "module": m.module,
                "role_reference": m.role_reference,
                "regulation_reference": m.regulation_reference,
                "risk_reference": m.risk_reference,
                "competency_reference": m.competency_reference,
                "behavioural_outcome": m.behavioural_outcome
            }
            for m in modules
        ]
        
        gen = TrainingPlanGenerator()
        evaluation = gen.evaluate_plan(plan.role, responsibilities, risks, current_modules)
        
        return {
            "plan_id": plan_id,
            "role": plan.role,
            "overall": evaluation.get("overall", 80),
            "dimensions": evaluation.get("dimensions", [])
        }
    finally:
        db.close()


@router.patch("/training/plans/{plan_id}")
def update_plan_status(plan_id: str, data: dict):
    """Patch endpoint to update status and reviewers notes of a plan"""
    db = SessionLocal()
    try:
        plan = db.query(TrainingPlan).filter_by(plan_id=plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        if "status" in data:
            plan.status = data["status"]
        if "reviewer_notes" in data:
            plan.reviewer_notes = data["reviewer_notes"]
            
        db.commit()
        return {"status": "success", "plan_id": plan_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error updating status: {str(e)}")
    finally:
        db.close()
