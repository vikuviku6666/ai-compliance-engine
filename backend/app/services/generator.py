import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.services.llm_service import client, MODEL, governed_llm_call
from app.services.compliance_engine import _competency_from_control
from app.rag.knowledge_index import KnowledgeIndexBuilder


def _build_scorecard(dimensions: List[Dict], weights: Dict[str, int]) -> Dict[str, Any]:
    """Attach weights to dimensions and calculate overall score — purely in Python.

    Args:
        dimensions: list of {name, score, message} from LLM
        weights:    dict of {dimension_name: weight_int} defined in code

    Returns:
        {overall, dimensions} where each dimension has weight and contribution added
    """
    total_weight = sum(weights.values())
    overall = 0
    result_dims = []

    for dim in dimensions:
        name   = dim.get("name", "")
        score  = max(0, min(100, int(dim.get("score", 0))))
        weight = weights.get(name, 0)
        contribution = round(score * weight / 100)
        overall += contribution
        result_dims.append({
            "name":         name,
            "score":        score,
            "message":      dim.get("message", ""),
            "weight":       weight,
            "contribution": contribution,
        })

    return {
        "overall":    max(0, min(100, overall)),
        "dimensions": result_dims,
    }


class TrainingPlanGenerator:
    """Orchestrates RAG-based 1-year training plan generation, evaluation, and revision"""

    def __init__(self):
        self.rag_builder = KnowledgeIndexBuilder()

    def extract_role_info(self, text: str) -> Dict[str, Any]:
        """Extract primary role name, responsibilities, and risks from raw text.
        Uses Neo4j governance graph to override LLM-extracted risks when available.
        """
        prompt = f"""
        Analyze the following role description text and extract:
        1. The primary Job Role Name.
        2. A list of 3-5 key compliance or operational responsibilities/duties of the role.
        3. A list of 3-5 primary regulatory or financial crime risks associated with this role.

        Provided Text:
        \"\"\"{text}\"\"\"

        Rules:
        - Only extract information that is explicitly stated or strongly implied in the text.
        - Do not invent risks that are not grounded in the text.

        Respond ONLY with a valid JSON object matching the following structure:
        {{
            "role": "KYC Analyst",
            "responsibilities": [
                "Verify customer identity documents during onboarding",
                "Perform enhanced due diligence on high-risk customers",
                "Conduct PEP and sanction screening checks"
            ],
            "risks": [
                "Identity theft and document fraud",
                "Money laundering via shell companies",
                "Sanctions circumvention"
            ]
        }}
        Do not include any pre-text, post-text, markdown tags, or extra characters. Respond with raw JSON only.
        """
        try:
            raw = governed_llm_call(
                prompt,
                response_format={"type": "json_object"}
            )
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            data = json.loads(raw)
            role = data.get("role", "Compliance Specialist")
            responsibilities = data.get("responsibilities", ["AML monitoring"])
            risks = data.get("risks", ["Financial crime exposure"])

            # Override risks with Neo4j governance graph data if available (Task 1.7)
            # The LLM NEVER decides risks — Neo4j is authoritative.
            try:
                from app.graph.neo4j_client import driver
                with driver.session() as session:
                    result = session.run(
                        """
                        MATCH (r:Role {name: $role})-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
                        MATCH (resp)-[:INTRODUCES]->(risk:Risk)
                        RETURN DISTINCT risk.name as risk_name
                        """,
                        role=role
                    )
                    graph_risks = [record["risk_name"] for record in result]
                    if graph_risks:
                        risks = graph_risks
            except Exception:
                pass

            return {
                "role": role,
                "responsibilities": responsibilities,
                "risks": risks
            }
        except Exception as e:
            print(f"Error extracting role details: {e}")
            return {
                "role": "Compliance Analyst",
                "responsibilities": [line.strip("- ") for line in text.split("\n") if line.strip()][:3],
                "risks": ["General AML compliance risks"]
            }

    def get_rag_context(self, responsibilities: List[str], risks: List[str]) -> str:
        """Query RAG index for relevant EU AMLR context based on responsibilities and risks"""
        retrieved_chunks = []
        seen_chunk_ids = set()

        # Query responsibilities -> retrieve deterministic Articles (obligations)
        for q in responsibilities[:3]:
            try:
                results = self.rag_builder.search_for_answer_type(q, "deterministic", limit=2)
                for r in results:
                    if r["chunk_id"] not in seen_chunk_ids:
                        seen_chunk_ids.add(r["chunk_id"])
                        retrieved_chunks.append(r)
            except Exception as e:
                print(f"⚠ RAG deterministic search failed (continuing): {e}")

        # Query risks -> retrieve explanatory Recitals (context/rationales)
        for q in risks[:3]:
            try:
                results = self.rag_builder.search_for_answer_type(q, "explanatory", limit=2)
                for r in results:
                    if r["chunk_id"] not in seen_chunk_ids:
                        seen_chunk_ids.add(r["chunk_id"])
                        retrieved_chunks.append(r)
            except Exception as e:
                print(f"⚠ RAG explanatory search failed (continuing): {e}")

        context_parts = []
        for i, chunk in enumerate(retrieved_chunks[:8]):
            section_info = chunk.get("section") or "General"
            legal_type = chunk.get("legal_type") or "general"
            obligation_type = chunk.get("obligation_type") or "EXPLANATORY"
            actor = chunk.get("actor") or "Obliged Entity"
            topic = chunk.get("topic") or "General Compliance"
            risk_category = chunk.get("risk_category") or "AML"
            content = chunk.get("content", "")

            # Formulate audit-grade rich citations for the LLM
            citation_header = f"[{section_info}] type={legal_type} | obligation={obligation_type} | topic={topic} | actor={actor} | risk={risk_category}"
            context_parts.append(
                f"--- Document Source Section: {citation_header} (ID: {chunk['chunk_id']}) ---\n{content}\n"
            )

        return "\n".join(context_parts)

    def generate_plan(self, role: str, responsibilities: List[str], risks: List[str], text_context: str) -> List[Dict[str, Any]]:
        """Synthesize 1-year training path using Neo4j compliance graph if available, falling back to LLM guided by RAG"""
        from app.services.roadmap_service import RoadmapService
        import re

        # 1. Attempt deterministic traversal from Neo4j compliance graph (preferred)
        paths = RoadmapService.traverse_compliance_path(role)
        if paths:
            def get_reg_num(p):
                reg = p.get("regulation", "")
                numbers = [int(s) for s in re.findall(r'\d+', reg)]
                return numbers[0] if numbers else 999
            paths.sort(key=get_reg_num)

            # Attach competency then sort Foundational → Intermediate → Advanced
            _order = {"Foundational": 0, "Intermediate": 1, "Advanced": 2}
            _q_seq = ["Q1 Foundation", "Q2 Application", "Q3 Deepening", "Q4 Embedding"]
            _q_key = {
                "Q1 Foundation": "Q1", "Q2 Application": "Q2",
                "Q3 Deepening":  "Q3", "Q4 Embedding":   "Q4",
            }

            for p in paths:
                p["_comp"] = _competency_from_control(p["control"], p["regulation"])
            paths.sort(key=lambda p: (_order.get(p["_comp"], 1), p.get("regulation", "")))

            recommendations = []
            for idx, path in enumerate(paths):
                quarter = _q_seq[idx % 4]
                recommendations.append({
                    "quarter": quarter,
                    "module": path["training"],
                    "role_reference": path["responsibility"],
                    "regulation_reference": path["regulation"],
                    "risk_reference": path["risk"],
                    "competency_reference": path["_comp"],
                    "behavioural_outcome": (
                        f"Implement {path['control']} controls to mitigate "
                        f"{path['risk']} under {path['regulation']} guidelines."
                    )
                })
            return recommendations

        # 2. LLM fallback guided by RAG context — regulations MUST come from context only
        prompt = f"""
        You are a senior compliance training architect. Create a comprehensive, premium, database-persistent 1-year (4-quarter) quarterly training path for the following job role.

        Job Role: {role}
        Core Responsibilities: {json.dumps(responsibilities, indent=2)}
        Financial Crime Risks: {json.dumps(risks, indent=2)}

        EU AMLR 2024/1624 Regulatory Context (retrieved from RAG database):
        {text_context}

        Your task is to generate exactly 5 to 6 distinct training activities or modules distributed across the 4 quarters:
        1. "Q1 Foundation" (Months 1-3)
        2. "Q2 Application" (Months 4-6)
        3. "Q3 Deepening" (Months 7-9)
        4. "Q4 Embedding" (Months 10-12)

        Each training module must map directly to:
        - One of the target role responsibilities.
        - One of the primary financial crime risks.
        - A specific Article or Recital reference from the EU AMLR context provided (e.g., "Article 13", "Article 19").

        CRITICAL: Only use regulation references that appear in the EU AMLR Regulatory Context provided above.
        Do not invent or add regulations that are not present in the context.

        Respond ONLY with a valid JSON array of objects representing the modules. Do not include markdown wraps or pre/post commentaries.

        Required JSON Object Structure for each module:
        {{
            "quarter": "Q1 Foundation",
            "module": "Course name (e.g. CDD Fundamentals)",
            "role_reference": "Specific responsibility mapped (e.g. Verify customer identity)",
            "regulation_reference": "Article 13: CDD Measures - AMLR 2024/1624",
            "risk_reference": "Specific risk mapped (e.g. Identity theft and document fraud)",
            "competency_reference": "Foundational",
            "behavioural_outcome": "Specific measurable action (e.g. Properly verify official documents and spot signs of forgery)"
        }}
        """
        try:
            raw = governed_llm_call(
                prompt,
                response_format={"type": "json_object"}
            )
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            result = json.loads(raw)
            if isinstance(result, dict):
                for key in ("modules", "plan", "training_modules"):
                    if key in result and isinstance(result[key], list):
                        result = result[key]
                        break
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Error generating training modules: {e}")
            return [
                {
                    "quarter": "Q1 Foundation",
                    "module": f"{role} Compliance Fundamentals",
                    "role_reference": responsibilities[0] if responsibilities else "General duties",
                    "regulation_reference": "Article 13: Customer Due Diligence",
                    "risk_reference": risks[0] if risks else "General compliance risk",
                    "competency_reference": "Foundational",
                    "behavioural_outcome": "Understand basic compliance policies"
                }
            ]

    def evaluate_plan(self, role: str, responsibilities: List[str], risks: List[str], modules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform strict quality scorecard evaluation across three dimensions.

        Weights are defined here in code — NOT by the LLM.
        LLM only returns raw scores (0-100) and explanatory messages.
        Python calculates weighted overall score deterministically.
        """
        # ── Weights defined in code — not by LLM ──────────────────────────────
        WEIGHTS = {
            "AML Regulation Relevance": 40,
            "Role Alignment":           30,
            "Risk & Control Coverage":  30,
        }

        prompt = f"""
        You are a senior compliance oversight auditor. Critically evaluate the training plan below.
        Be strict and objective. Do NOT inflate scores. Most plans should score 50-75 unless they are genuinely comprehensive.

        Target Role: {role}
        Responsibilities: {json.dumps(responsibilities)}
        Inherent Risks: {json.dumps(risks)}

        Training Plan Modules:
        {json.dumps(modules, indent=2)}

        Score each dimension from 0 to 100 using the rubric below:

        DIMENSION 1 — AML Regulation Relevance
        - 90-100: Every module cites a specific EU AMLR 2024/1624 article or recital number. Citations are accurate.
        - 70-89:  Most modules cite articles. 1-2 modules have vague or missing references.
        - 50-69:  Several modules lack specific article citations. References are generic.
        - 30-49:  Fewer than half the modules cite specific articles.
        - 0-29:   No meaningful regulation citations.

        DIMENSION 2 — Role Alignment
        - 90-100: Every module maps directly to a stated responsibility of the role.
        - 70-89:  Most modules are role-relevant. Minor gaps.
        - 50-69:  Some modules are generic and not specific to this role's duties.
        - 30-49:  Significant mismatch between role responsibilities and training content.
        - 0-29:   Training content is largely irrelevant to the role.

        DIMENSION 3 — Risk & Control Coverage
        - 90-100: Every identified inherent risk has at least one training module with a mapped control.
        - 70-89:  Most risks covered. 1 risk may be missing.
        - 50-69:  Only about half the risks are addressed.
        - 30-49:  Most risks are not covered by training modules.
        - 0-29:   No meaningful risk-control mapping.

        Respond ONLY with this exact JSON structure. Do NOT include weights or overall — those are calculated separately.
        Do not include pre-text, post-text, or markdown:
        {{
            "dimensions": [
                {{
                    "name": "AML Regulation Relevance",
                    "score": <integer 0-100>,
                    "message": "<1 sentence explaining the score with specific evidence from the modules>"
                }},
                {{
                    "name": "Role Alignment",
                    "score": <integer 0-100>,
                    "message": "<1 sentence explaining the score with specific evidence from the modules>"
                }},
                {{
                    "name": "Risk & Control Coverage",
                    "score": <integer 0-100>,
                    "message": "<1 sentence — list which risks are covered and which are missing>"
                }}
            ]
        }}
        """
        try:
            raw = governed_llm_call(
                prompt,
                response_format={"type": "json_object"}
            )
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            result = json.loads(raw)
            dimensions = result.get("dimensions", [])

            # ── Calculate overall + inject weights in Python — not LLM ────────
            return _build_scorecard(dimensions, WEIGHTS)

        except Exception as e:
            print(f"Error evaluating plan: {e}")
            # Deterministic fallback from module data
            has_articles = sum(
                1 for m in modules
                if any(kw in str(m.get("regulation_reference", "")).lower()
                       for kw in ["article", "recital"])
            )
            total = max(len(modules), 1)
            reg_score  = min(100, round(has_articles / total * 100))
            risks_in_modules = {
                str(m.get("risk_reference", m.get("risk", ""))).lower()
                for m in modules
            }
            risks_covered = sum(
                1 for r in risks
                if any(word in risks_in_modules for word in r.lower().split() if len(word) > 4)
            )
            risk_score  = min(100, round(risks_covered / max(len(risks), 1) * 100))
            resps_in_modules = {
                str(m.get("role_reference", m.get("responsibility", ""))).lower()
                for m in modules
            }
            resps_covered = sum(
                1 for r in responsibilities
                if any(word in resps_in_modules for word in r.lower().split() if len(word) > 4)
            )
            role_score = min(100, round(resps_covered / max(len(responsibilities), 1) * 100))

            dimensions = [
                {"name": "AML Regulation Relevance", "score": reg_score,
                 "message": f"{has_articles}/{total} modules cite specific EU AMLR articles or recitals."},
                {"name": "Role Alignment", "score": role_score,
                 "message": f"{resps_covered}/{len(responsibilities)} responsibilities mapped to training modules."},
                {"name": "Risk & Control Coverage", "score": risk_score,
                 "message": f"{risks_covered}/{len(risks)} inherent risks covered by training modules."},
            ]
            return _build_scorecard(dimensions, WEIGHTS)

    def revise_plan(self, plan_id: str, current_role: str, current_responsibilities: List[str], current_risks: List[str], current_modules: List[Dict[str, Any]], feedback: str) -> List[Dict[str, Any]]:
        """Intelligently revise existing plan based on reviewer's feedback"""
        prompt = f"""
        You are a senior compliance training architect. Revise the existing training plan based on the reviewer's feedback.

        Job Role: {current_role}
        Core Responsibilities: {json.dumps(current_responsibilities)}
        Financial Crime Risks: {json.dumps(current_risks)}

        Current Training Plan:
        {json.dumps(current_modules, indent=2)}

        Reviewer's Feedback / Revision Requests:
        \"\"\"{feedback}\"\"\"

        Incorporate this feedback comprehensively while maintaining the same premium quality.
        Distribute 5 to 6 activities across the 4 quarters:
        - "Q1 Foundation"
        - "Q2 Application"
        - "Q3 Deepening"
        - "Q4 Embedding"

        CRITICAL: Only use regulation references that were in the original plan or are well-established EU AMLR 2024/1624 articles.
        Do not invent regulations not grounded in the original plan context.

        Respond ONLY with a valid JSON array of objects representing the modules. Do not include markdown wraps or pre/post commentaries.

        Required JSON Object Structure for each module:
        {{
            "quarter": "Q1 Foundation",
            "module": "Course name (e.g. CDD Fundamentals)",
            "role_reference": "Specific responsibility mapped",
            "regulation_reference": "Article 13: CDD Measures - AMLR 2024/1624",
            "risk_reference": "Specific risk mapped",
            "competency_reference": "Foundational",
            "behavioural_outcome": "Specific measurable action"
        }}
        """
        try:
            raw = governed_llm_call(
                prompt,
                response_format={"type": "json_object"}
            )
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

            result = json.loads(raw)
            if isinstance(result, dict):
                for key in ("modules", "plan", "training_modules"):
                    if key in result and isinstance(result[key], list):
                        result = result[key]
                        break
            return result if isinstance(result, list) else current_modules
        except Exception as e:
            print(f"Error revising plan: {e}")
            return current_modules
