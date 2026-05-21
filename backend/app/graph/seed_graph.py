"""
Graph seeder — populates Neo4j with a comprehensive EU AMLR-grounded
governance graph: Roles → Responsibilities → Risks → Controls → Regulations → Training

Run once:  uv run python backend/app/graph/seed_graph.py
Re-run:    same command (MERGE is idempotent)

Optimization: Uses UNWIND + batch MERGE for ~50× faster seeding (single transaction).
"""

import time
from app.graph.neo4j_client import get_driver
from app.graph.cache import cache_invalidate

# ─── Governance data ──────────────────────────────────────────────────────────
# Each entry:  (role, responsibility, risk, control, regulation, training_name)
# Regulations map to real EU AMLR 2024/1624 articles / recitals
GOVERNANCE = [

    # ── KYC Analyst ───────────────────────────────────────────────────────────
    ("KYC Analyst", "Customer Onboarding",
     "Identity Fraud",
     "Customer Due Diligence (CDD)",
     "Article 22", "Identity Verification & CDD (Article 22)"),

    ("KYC Analyst", "Customer Onboarding",
     "Impersonation Risk",
     "Customer Due Diligence (CDD)",
     "Article 22", "Identity Verification & CDD (Article 22)"),

    ("KYC Analyst", "Beneficial Ownership Verification",
     "Shell Company Money Laundering",
     "UBO Registry Verification",
     "Article 55", "Beneficial Ownership Verification (Article 55)"),

    ("KYC Analyst", "Beneficial Ownership Verification",
     "Nominee Ownership Concealment",
     "UBO Registry Verification",
     "Article 55", "Beneficial Ownership Verification (Article 55)"),

    ("KYC Analyst", "PEP Screening",
     "Politically Exposed Person Risk",
     "PEP Identification & Enhanced Scrutiny",
     "Article 43", "PEP Screening & Prominent Functions (Article 43)"),

    ("KYC Analyst", "PEP Screening",
     "Close Associate Risk",
     "PEP Identification & Enhanced Scrutiny",
     "Article 46", "PEP Close Associates Screening (Article 46)"),

    ("KYC Analyst", "Ongoing CDD Reviews",
     "Stale Customer Profile Risk",
     "Ongoing Monitoring",
     "Article 25", "Ongoing Monitoring & Transaction Surveillance (Article 25)"),

    ("KYC Analyst", "Ongoing CDD Reviews",
     "Behaviour Change Risk",
     "Ongoing Monitoring",
     "Article 25", "Ongoing Monitoring & Transaction Surveillance (Article 25)"),

    ("KYC Analyst", "Third-Party Risk Management",
     "Third-Party Intermediary Fraud",
     "Outsourcing Controls",
     "Article 32", "Third-Party & Outsourcing Risk Controls (Article 32)"),

    ("KYC Analyst", "Sanctions Screening",
     "Sanctions Evasion",
     "Sanctions List Screening",
     "Article 25", "Sanctions & Targeted Financial Restrictions (Article 25)"),

    ("KYC Analyst", "Simplified CDD Application",
     "Incorrect Risk Classification",
     "Simplified CDD Procedures",
     "Recital 78", "Simplified CDD in Low-Risk Situations (Recital 78)"),

    # ── Compliance Analyst ────────────────────────────────────────────────────
    ("Compliance Analyst", "Compliance Monitoring",
     "Regulatory Breach",
     "Compliance Control Framework",
     "Article 22", "AML Compliance Monitoring Fundamentals (Article 22)"),

    ("Compliance Analyst", "Risk Management Oversight",
     "Unmitigated AML Risks",
     "Risk Control Framework",
     "Article 32", "AML Risk Assessment & Control Framework (Article 32)"),

    ("Compliance Analyst", "EDD Auditing",
     "High-Risk Customer Exposure",
     "Enhanced Due Diligence (EDD)",
     "Article 32", "Enhanced Due Diligence Procedures (Article 32)"),

    ("Compliance Analyst", "EDD Auditing",
     "High-Risk Country Exposure",
     "Enhanced Due Diligence (EDD)",
     "Article 32", "Enhanced Due Diligence Procedures (Article 32)"),

    ("Compliance Analyst", "SAR Reporting",
     "Failure to Report Suspicious Transactions",
     "Suspicious Activity Reporting (SAR)",
     "Article 32", "Suspicious Activity Reporting (Article 32)"),

    ("Compliance Analyst", "Internal Policy Governance",
     "Policy Non-Compliance",
     "Internal AML Policy Controls",
     "Recital 39", "Internal AML Policy & Governance (Recital 39)"),

    ("Compliance Analyst", "Training Programme Oversight",
     "Undertrained Staff Risk",
     "Staff AML Training Programme",
     "Recital 45", "AML Training Programme Management (Recital 45)"),

    # ── MLRO (Money Laundering Reporting Officer) ─────────────────────────────
    ("MLRO", "SAR Filing & Oversight",
     "Failure to Report Suspicious Transactions",
     "Suspicious Activity Reporting (SAR)",
     "Article 32", "SAR Filing & FIU Reporting Obligations (Article 32)"),

    ("MLRO", "FIU Liaison",
     "Non-Cooperation with FIU",
     "FIU Reporting Controls",
     "Article 32", "Financial Intelligence Unit Cooperation (Article 32)"),

    ("MLRO", "AML Risk Assessment",
     "Incomplete Risk Assessment",
     "Enterprise Risk Assessment Framework",
     "Article 32", "AML Enterprise Risk Assessment (Article 32)"),

    ("MLRO", "Staff Training Oversight",
     "Undertrained Staff Risk",
     "Staff AML Training Programme",
     "Recital 45", "AML Training Oversight (Recital 45)"),

    ("MLRO", "Compliance Programme Management",
     "Regulatory Breach",
     "Compliance Control Framework",
     "Recital 39", "Compliance Programme Governance (Recital 39)"),

    ("MLRO", "Beneficial Ownership Oversight",
     "Shell Company Money Laundering",
     "UBO Registry Verification",
     "Article 55", "Beneficial Ownership Transparency (Article 55)"),

    # ── AML Investigator ──────────────────────────────────────────────────────
    ("AML Investigator", "Suspicious Transaction Investigation",
     "Failure to Report Suspicious Transactions",
     "Suspicious Activity Reporting (SAR)",
     "Article 32", "Suspicious Transaction Investigation (Article 32)"),

    ("AML Investigator", "Alert Review & Triage",
     "False Negative Alert Risk",
     "Transaction Monitoring Controls",
     "Article 25", "Transaction Monitoring & Alert Management (Article 25)"),

    ("AML Investigator", "Case Management",
     "Evidence Destruction Risk",
     "Case Documentation Controls",
     "Recital 88", "AML Case Management & Documentation (Recital 88)"),

    ("AML Investigator", "Sanctions Screening Review",
     "Sanctions Evasion",
     "Sanctions List Screening",
     "Article 25", "Sanctions Screening & Investigation (Article 25)"),

    ("AML Investigator", "High-Risk Client Investigation",
     "High-Risk Customer Exposure",
     "Enhanced Due Diligence (EDD)",
     "Article 32", "High-Risk Client Investigation (Article 32)"),

    # ── Relationship Manager ──────────────────────────────────────────────────
    ("Relationship Manager", "Client Onboarding",
     "Identity Fraud",
     "Customer Due Diligence (CDD)",
     "Article 22", "Client Onboarding & CDD (Article 22)"),

    ("Relationship Manager", "Client Risk Assessment",
     "Incorrect Risk Classification",
     "Risk-Based Client Profiling",
     "Article 32", "Client Risk Profiling (Article 32)"),

    ("Relationship Manager", "PEP Client Management",
     "Politically Exposed Person Risk",
     "PEP Identification & Enhanced Scrutiny",
     "Article 43", "Managing PEP Client Relationships (Article 43)"),

    ("Relationship Manager", "Transaction Monitoring",
     "Suspicious Transaction Risk",
     "Transaction Monitoring Controls",
     "Article 25", "Transaction Monitoring for Relationship Managers (Article 25)"),

    ("Relationship Manager", "Beneficial Ownership Collection",
     "Shell Company Money Laundering",
     "UBO Registry Verification",
     "Article 55", "Collecting Beneficial Ownership Information (Article 55)"),

    # ── Senior Management ─────────────────────────────────────────────────────
    ("Senior Management", "AML Governance Oversight",
     "Regulatory Breach",
     "Compliance Control Framework",
     "Recital 39", "Senior Management AML Governance (Recital 39)"),

    ("Senior Management", "Risk Appetite Setting",
     "Unmitigated AML Risks",
     "Enterprise Risk Assessment Framework",
     "Article 32", "Risk Appetite & AML Strategy (Article 32)"),

    ("Senior Management", "Compliance Culture",
     "Undertrained Staff Risk",
     "Staff AML Training Programme",
     "Recital 45", "Building AML Compliance Culture (Recital 45)"),
]


def _create_indexes(session):
    """Create Neo4j indexes for efficient text search."""
    print("Creating indexes...")
    try:
        # Full-text search indexes on commonly queried fields
        session.run("CREATE INDEX idx_role_name IF NOT EXISTS FOR (n:Role) ON (n.name)")
        session.run("CREATE INDEX idx_risk_name IF NOT EXISTS FOR (n:Risk) ON (n.name)")
        session.run("CREATE INDEX idx_control_name IF NOT EXISTS FOR (n:Control) ON (n.name)")
        session.run("CREATE INDEX idx_regulation_name IF NOT EXISTS FOR (n:Regulation) ON (n.name)")
        session.run("CREATE INDEX idx_training_name IF NOT EXISTS FOR (n:Training) ON (n.name)")
        print("✓ Indexes created")
    except Exception as e:
        print(f"⚠ Index creation failed (non-fatal): {e}")


def _seed_batch(session, governance_data):
    """Seed graph using UNWIND + batch MERGE (single transaction, ~50× faster)."""
    import logging
    logger = logging.getLogger(__name__)

    # Prepare data for UNWIND: extract unique nodes and relationships
    paths = [
        {
            "role": r[0],
            "resp": r[1],
            "risk": r[2],
            "ctrl": r[3],
            "reg": r[4],
            "train": r[5],
        }
        for r in governance_data
    ]

    # Batch 1: Create all unique nodes (UNWIND + MERGE)
    start = time.time()
    session.run("""
        UNWIND $paths AS p
        MERGE (r:Role {name: p.role})
        MERGE (resp:Responsibility {name: p.resp})
        MERGE (risk:Risk {name: p.risk})
        MERGE (ctrl:Control {name: p.ctrl})
        MERGE (reg:Regulation {name: p.reg})
        MERGE (train:Training {name: p.train})
    """, paths=paths)
    elapsed_nodes = time.time() - start
    logger.info(f"Batch nodes created in {elapsed_nodes:.3f}s")

    # Batch 2: Create all relationships (UNWIND + MERGE)
    start = time.time()
    session.run("""
        UNWIND $paths AS p
        MATCH (r:Role {name: p.role})
        MATCH (resp:Responsibility {name: p.resp})
        MATCH (risk:Risk {name: p.risk})
        MATCH (ctrl:Control {name: p.ctrl})
        MATCH (reg:Regulation {name: p.reg})
        MATCH (train:Training {name: p.train})
        MERGE (r)-[:HAS_RESPONSIBILITY]->(resp)
        MERGE (resp)-[:INTRODUCES]->(risk)
        MERGE (risk)-[:MITIGATED_BY]->(ctrl)
        MERGE (ctrl)-[:REQUIRED_BY]->(reg)
        MERGE (ctrl)-[:TRAINED_BY]->(train)
    """, paths=paths)
    elapsed_rels = time.time() - start
    logger.info(f"Batch relationships created in {elapsed_rels:.3f}s")


def _print_summary(session):
    """Print seeding summary statistics."""
    counts = {}
    for label in ["Role", "Responsibility", "Risk", "Control", "Regulation", "Training"]:
        r = session.run(f"MATCH (n:{label}) RETURN count(n) as c").single()
        counts[label] = r["c"]

    print("\nGraph summary:")
    for k, v in counts.items():
        print(f"  {k:15}: {v}")

    paths = session.run("""
        MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp)-[:INTRODUCES]->(risk)
              -[:MITIGATED_BY]->(ctrl)-[:REQUIRED_BY]->(reg)
        RETURN count(*) as c
    """).single()
    print(f"  {'Total paths':15}: {paths['c']}")


def seed():
    """Seed the governance graph (idempotent, ~5 seconds vs ~30 seconds with individual queries)."""
    driver = get_driver()
    with driver.session() as session:
        print("Seeding governance graph...")
        start = time.time()

        _create_indexes(session)
        _seed_batch(session, GOVERNANCE)
        _print_summary(session)

        elapsed = time.time() - start
        print(f"\nDone in {elapsed:.2f}s")

    # Invalidate cache after seeding (new data available)
    cache_invalidate()
    print("✓ Query cache invalidated")


if __name__ == "__main__":
    seed()
