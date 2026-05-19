"""
Graph seeder — populates Neo4j with a comprehensive EU AMLR-grounded
governance graph: Roles → Responsibilities → Risks → Controls → Regulations → Training

Run once:  uv run python backend/app/graph/seed_graph.py
Re-run:    same command (MERGE is idempotent)
"""

from app.graph.neo4j_client import driver

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


def seed():
    with driver.session() as session:
        # Clear old structure nodes (keep existing test data)
        print("Seeding governance graph...")

        for (role, resp, risk, control, regulation, training) in GOVERNANCE:
            # MERGE all nodes
            session.run("MERGE (:Role {name: $n})", n=role)
            session.run("MERGE (:Responsibility {name: $n})", n=resp)
            session.run("MERGE (:Risk {name: $n})", n=risk)
            session.run("MERGE (:Control {name: $n})", n=control)
            session.run("MERGE (:Regulation {name: $n})", n=regulation)
            session.run("MERGE (:Training {name: $n})", n=training)

            # MERGE all relationships (idempotent)
            session.run("""
                MATCH (r:Role {name:$role}), (resp:Responsibility {name:$resp})
                MERGE (r)-[:HAS_RESPONSIBILITY]->(resp)
            """, role=role, resp=resp)

            session.run("""
                MATCH (resp:Responsibility {name:$resp}), (risk:Risk {name:$risk})
                MERGE (resp)-[:INTRODUCES]->(risk)
            """, resp=resp, risk=risk)

            session.run("""
                MATCH (risk:Risk {name:$risk}), (ctrl:Control {name:$ctrl})
                MERGE (risk)-[:MITIGATED_BY]->(ctrl)
            """, risk=risk, ctrl=control)

            session.run("""
                MATCH (ctrl:Control {name:$ctrl}), (reg:Regulation {name:$reg})
                MERGE (ctrl)-[:REQUIRED_BY]->(reg)
            """, ctrl=control, reg=regulation)

            session.run("""
                MATCH (ctrl:Control {name:$ctrl}), (t:Training {name:$t})
                MERGE (ctrl)-[:TRAINED_BY]->(t)
            """, ctrl=control, t=training)

        # Print summary
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
        print("\nDone.")


if __name__ == "__main__":
    seed()
