import json
from typing import List, Dict, Any
from app.graph.neo4j_client import get_driver
from app.db.database import SessionLocal
from app.services.llm_service import client, MODEL, SYSTEM_MENTAL_MODEL
from app.services.validators import validate_governance_boundaries
from sqlalchemy import text

class RoadmapService:
    """Deterministic traverser of compliance paths and legal evidence compiler"""

    @staticmethod
    def traverse_compliance_path(role_name: str) -> List[Dict[str, Any]]:
        """Traverse Neo4j path deterministically: Role -> Responsibility -> Risk -> Control -> Regulation & Training"""
        query = """
        MATCH (r:Role {name: $role})
        MATCH (r)-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
        MATCH (resp)-[:INTRODUCES]->(risk:Risk)
        MATCH (risk)-[:MITIGATED_BY]->(control:Control)
        MATCH (control)-[:REQUIRED_BY]->(reg:Regulation)
        MATCH (control)-[:TRAINED_BY]->(training:Training)
        RETURN DISTINCT
            resp.name as responsibility,
            risk.name as risk,
            control.name as control,
            reg.name as regulation,
            training.name as training
        """
        with get_driver().session() as session:
            result = session.run(query, role=role_name)
            return [dict(r) for r in result]

    @staticmethod
    def get_legal_evidence(regulation_name: str, control_name: str = "") -> str:
        """Retrieve audit-grade regulatory evidence using hybrid search + evidence chain assembly.

        Phase 5 upgrade: uses KnowledgeIndexBuilder.assemble_evidence_chain()
        which combines targeted article/recital lookup, keyword search, and
        vector similarity — with proper citations.
        """
        try:
            from app.rag.knowledge_index import KnowledgeIndexBuilder
            builder = KnowledgeIndexBuilder()
            evidence = builder.assemble_evidence_chain(
                regulation_name=regulation_name,
                control_name=control_name,
                limit=3
            )
            return evidence
        except Exception as e:
            print(f"Error fetching legal evidence: {e}")
            return "Regulatory text not available."

    @staticmethod
    def generate_summary(training: str, control: str, regulation: str, evidence: str) -> str:
        """Generate an audit-ready training module summary strictly grounded in legal evidence."""
        prompt = f"""
        You are an enterprise compliance training summarizer. Generate a concise, objective summary of the following training module.
        You must base your summary STRICTLY on the legal evidence text provided. Do not extrapolate, infer, or invent any compliance rules.

        Training Module Name: {training}
        Target Control: {control}
        Regulation Reference: {regulation}
        Legal Evidence:
        \"\"\"{evidence}\"\"\"

        Provide a concise, professional 2-3 sentence overview explaining exactly what is covered in this training according to the regulation.
        Do not add any preamble or generic intro.
        """
        try:
            from app.services.llm_service import governed_llm_call
            response = governed_llm_call(prompt)
            return response.strip()
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Overview course covering {training} to satisfy control {control} pursuant to {regulation}."
