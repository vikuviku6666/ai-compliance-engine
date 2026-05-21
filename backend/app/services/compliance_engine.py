"""
Compliance Engine — Core Service

Flow:
    Input: role + responsibilities + inherent_risks
        ↓
    1. Neo4j graph traversal (deterministic governance)
        ↓
    2. For each risk → find regulation from knowledge index (EU AMLR)
        ↓
    3. Map regulation → control (governance-defined)
        ↓
    4. Assemble evidence chain from knowledge index
        ↓
    5. LLM generates training module description (strictly grounded)
        ↓
    Output: 4-quarter training plan with full explainability trace
            (role → responsibility → risk → article_num → control → training)
"""

import json
import re
from typing import List, Dict, Any, Optional
import concurrent.futures
from app.graph.neo4j_client import get_driver
from app.rag.knowledge_index import KnowledgeIndexBuilder
from app.services.llm_service import governed_llm_call


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _resolve_regulation_to_article(regulation_name: str) -> tuple:
    """Resolve a regulation name (which may be a Recital) to its real Article number dynamically using PostgreSQL."""
    if not regulation_name:
        return regulation_name, None

    m = re.search(r'(\d+)', regulation_name)
    num = int(m.group(1)) if m else None

    if regulation_name.lower().startswith("recital") and num:
        try:
            from app.db.database import SessionLocal
            from sqlalchemy import text
            with SessionLocal() as db_session:
                closest_art = db_session.execute(text("""
                    SELECT article_num FROM knowledge_chunks
                    WHERE recital_num = :rec AND article_num IS NOT NULL
                    LIMIT 1
                """), {"rec": num}).scalar()
                if closest_art:
                    return f"Article {closest_art}", closest_art
        except Exception as e:
            print(f"⚠ Failed to dynamically resolve Recital to Article (using fallback): {e}")

    return regulation_name, num


def _extract_article_num(regulation_name: str) -> Optional[int]:
    """Extract integer article/recital number from a regulation string."""
    _, num = _resolve_regulation_to_article(regulation_name)
    return num


def _quarter_label(idx: int) -> str:
    return ["Q1 Foundation", "Q2 Application", "Q3 Deepening", "Q4 Embedding"][idx % 4]


# Controls that require foundational knowledge (entry-level understanding)
_FOUNDATIONAL_CONTROLS = {
    "customer due diligence", "cdd", "kyc", "identity verification",
    "sanctions list screening", "simplified cdd", "basic aml",
}

# Controls that require advanced / specialist capability
_ADVANCED_CONTROLS = {
    "enhanced due diligence", "edd", "ubo registry verification",
    "suspicious activity reporting", "sar", "fiu reporting",
    "enterprise risk assessment", "case documentation",
    "compliance programme", "pep identification",
}

def _competency_from_control(control: str, regulation: str) -> str:
    """Derive competency level from the actual control and regulation — not from quarter position.

    Rules:
    - EDD, SAR, UBO, FIU, PEP, Enterprise-level controls → Advanced
    - Basic CDD, KYC, Sanctions screening → Foundational
    - Everything else → Intermediate
    - Recitals (policy/context) are always Foundational
    - High article numbers (Article 43+) tend to be specialist → Advanced
    """
    c_lower = control.lower()
    r_lower = regulation.lower()

    # Recitals = policy context = foundational
    if "recital" in r_lower:
        return "Foundational"

    # Check advanced controls
    if any(kw in c_lower for kw in _ADVANCED_CONTROLS):
        return "Advanced"

    # Check foundational controls
    if any(kw in c_lower for kw in _FOUNDATIONAL_CONTROLS):
        return "Foundational"

    # High article numbers tend to be specialist topics
    article_num = _extract_article_num(regulation)
    if article_num and article_num >= 43:
        return "Advanced"
    if article_num and article_num <= 22:
        return "Foundational"

    return "Intermediate"


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Neo4j — deterministic governance traversal
# ──────────────────────────────────────────────────────────────────────────────

def get_governed_paths(role: str) -> List[Dict[str, Any]]:
    """Traverse Neo4j for the full compliance path of a role.
    Falls back to fuzzy matching if exact role name not found.
    """
    query = """
    MATCH (r:Role)-[:HAS_RESPONSIBILITY]->(resp:Responsibility)
    MATCH (resp)-[:INTRODUCES]->(risk:Risk)
    MATCH (risk)-[:MITIGATED_BY]->(ctrl:Control)
    MATCH (ctrl)-[:REQUIRED_BY]->(reg:Regulation)
    MATCH (ctrl)-[:TRAINED_BY]->(t:Training)
    WHERE toLower(r.name) = toLower($role)
       OR toLower(r.name) CONTAINS toLower($role)
       OR toLower($role) CONTAINS toLower(r.name)
    RETURN DISTINCT
        r.name     AS matched_role,
        resp.name  AS responsibility,
        risk.name  AS risk,
        ctrl.name  AS control,
        reg.name   AS regulation,
        t.name     AS training
    ORDER BY reg.name
    """
    with get_driver().session() as session:
        rows = session.run(query, role=role)
        paths = []
        for r in rows:
            d = dict(r)
            resolved_reg, resolved_art = _resolve_regulation_to_article(d["regulation"])
            d["regulation"] = resolved_reg
            d["article_num"] = resolved_art
            paths.append(d)
        return paths


def get_graph_controls_for_risks(risks: List[str]) -> List[Dict[str, Any]]:
    """For each risk, find controls and regulations from Neo4j (fuzzy match)."""
    results = []
    seen = set()
    with get_driver().session() as session:
        for risk in risks:
            rows = session.run("""
                MATCH (risk:Risk)-[:MITIGATED_BY]->(ctrl:Control)
                      -[:REQUIRED_BY]->(reg:Regulation)
                      --(t:Training)
                WHERE toLower(risk.name) CONTAINS toLower($risk)
                   OR toLower($risk) CONTAINS toLower(risk.name)
                OPTIONAL MATCH (resp:Responsibility)-[:INTRODUCES]->(risk)
                RETURN DISTINCT
                    risk.name  AS matched_risk,
                    resp.name  AS responsibility,
                    ctrl.name  AS control,
                    reg.name   AS regulation,
                    t.name     AS training
            """, risk=risk)
            for r in rows:
                key = (r["matched_risk"], r["regulation"])
                if key in seen:
                    continue
                seen.add(key)
                d = dict(r)
                resolved_reg, resolved_art = _resolve_regulation_to_article(d["regulation"])
                d["regulation"] = resolved_reg
                d["article_num"] = resolved_art
                d["original_risk"] = risk
                results.append(d)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Knowledge index — find regulations that address each risk
# ──────────────────────────────────────────────────────────────────────────────

def find_regulations_for_risks(
    risks: List[str],
    responsibilities: List[str],
    limit_per_risk: int = 2
) -> List[Dict[str, Any]]:
    """Search EU AMLR knowledge index to find articles/recitals relevant to each risk.

    Returns list of dicts:
        risk, regulation, article_num, recital_num, legal_type, evidence_snippet
    """
    builder = KnowledgeIndexBuilder()
    results = []
    seen_sections: set = set()

    for risk in risks:
        hits = builder.search(risk, limit=limit_per_risk)
        for h in hits:
            section = h["section"]
            if section in seen_sections or section == "General":
                continue
            seen_sections.add(section)

            article_num = h.get("article_num")
            recital_num = h.get("recital_num")

            # Dynamic Article number resolution for Recitals
            resolved_reg, resolved_art = _resolve_regulation_to_article(section)

            results.append({
                "risk":             risk,
                "regulation":       resolved_reg,
                "article_num":      resolved_art or article_num,
                "recital_num":      recital_num,
                "legal_type":       h["legal_type"],
                "evidence_snippet": h["content"][:400],
            })

    # Also search responsibilities to catch training-related articles
    for resp in responsibilities[:3]:
        hits = builder.search(resp, limit=1)
        for h in hits:
            section = h["section"]
            if section in seen_sections or section == "General":
                continue
            seen_sections.add(section)

            article_num = h.get("article_num")
            recital_num = h.get("recital_num")

            # Dynamic Article number resolution for Recitals
            resolved_reg, resolved_art = _resolve_regulation_to_article(section)

            results.append({
                "risk":             resp,          # responsibility itself as the driver
                "regulation":       resolved_reg,
                "article_num":      resolved_art or article_num,
                "recital_num":      recital_num,
                "legal_type":       h["legal_type"],
                "evidence_snippet": h["content"][:400],
            })

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: LLM — generate training module description (grounded in evidence)
# ──────────────────────────────────────────────────────────────────────────────

def _deterministic_description(
    role: str,
    responsibility: str,
    risk: str,
    control: str,
    regulation_ref: str,
) -> str:
    """Build a module description from governance data — no LLM, instant.

    Used for modules sourced directly from the Neo4j governance graph
    where all entities are already well-defined.
    """
    return (
        f"This module equips {role}s to fulfil their responsibility of {responsibility} "
        f"by implementing {control} controls. "
        f"It directly mitigates the risk of {risk} as required by {regulation_ref}."
    )


def generate_module_name(
    role: str,
    responsibility: str,
    risk: str,
    control: str,
    regulation_ref: str,
    domain: str = "Banking & Payments",
) -> str:
    """Generate a professional, human-readable training module name using LLM.

    Keeps the article reference separate — this function returns only the name,
    e.g. "Customer Due Diligence for High-Risk Onboarding" not "CDD — Art.22".

    Falls back to a clean deterministic name if LLM fails.
    """
    prompt = f"""
    Generate a concise, professional training module name (4-8 words) for the following compliance context.

    Compliance Domain / Sector: {domain}
    Role:           {role}
    Responsibility: {responsibility}
    Risk:           {risk}
    Control:        {control}
    Regulation:     {regulation_ref}

    Rules:
    - Return ONLY the module name — no article reference, no quotes, no punctuation at the end
    - It should sound like a real professional training course title
    - It must reflect the specific risk and control (not generic) and be relevant to the {domain} sector
    - Examples of good names:
        "Customer Due Diligence for High-Risk Onboarding"
        "Suspicious Activity Reporting Obligations"
        "Beneficial Ownership Verification Fundamentals"
        "PEP Screening and Enhanced Scrutiny"
        "Sanctions Evasion Risk and Controls"
    - If the domain is Crypto/Virtual Assets, use crypto-specific context (e.g. "Crypto Wallet Identity Checks" instead of general "CDD").
    - Do NOT include article numbers in the name
    """
    try:
        name = governed_llm_call(prompt).strip().strip('"').strip("'").rstrip(".")
        # Sanity check — must be between 3 and 12 words
        if 3 <= len(name.split()) <= 12:
            return name
        # Too long or too short — fall through to fallback
    except Exception as e:
        print(f"Module name generation error: {e}")

    # Clean deterministic fallback
    return f"{control} — {responsibility}"


def generate_module_description(
    role: str,
    responsibility: str,
    risk: str,
    control: str,
    regulation: str,
    article_num: Optional[int],
    evidence: str,
    domain: str = "Banking & Payments",
) -> str:
    """Generate a concise, audit-safe training module description.

    The LLM is strictly constrained to the evidence text provided.
    """
    article_ref = f"Article {article_num}" if article_num else regulation
    prompt = f"""
    Generate a concise 2-3 sentence training module description for the following governance context.
    Base it STRICTLY on the Legal Evidence provided. Do not add information not in the evidence.

    Compliance Domain / Sector: {domain}
    Role:               {role}
    Responsibility:     {responsibility}
    Inherent Risk:      {risk}
    Mitigating Control: {control}
    Regulation:         {regulation} ({article_ref} — EU AMLR 2024/1624)

    Legal Evidence:
    \"\"\"{evidence}\"\"\"

    Output: A professional 2-3 sentence description explaining what this training module covers,
    tailored to the {domain} sector, and why it is required by {article_ref}. Do not invent controls or regulations.
    """
    try:
        return governed_llm_call(prompt).strip()
    except Exception as e:
        print(f"LLM description error: {e}")
        return (
            f"This module covers {control} requirements under {regulation} "
            f"to mitigate {risk} for staff with responsibility for {responsibility}."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main engine: assemble the full training plan
# ──────────────────────────────────────────────────────────────────────────────

def build_compliance_training_plan(
    role: str,
    responsibilities: List[str],
    inherent_risks: List[str],
    domain: str = "Banking & Payments",
) -> Dict[str, Any]:
    """Core engine: role + responsibilities + inherent_risks + domain → 4-quarter training plan.

    Strategy:
    1. Try Neo4j graph traversal first (deterministic governance).
    2. Augment with knowledge-index regulation lookup for any risks not covered.
    3. Deduplicate and sort by article number.
    4. Assign to quarters, generate LLM descriptions, attach full trace.

    Returns:
        {
          "role": ...,
          "plan": [
            {
              "quarter":            "Q1 Foundation",
              "module":             "CDD Fundamentals",
              "responsibility":     "Customer Onboarding",
              "risk":               "Identity Fraud",
              "control":            "CDD",
              "regulation":         "Article 13",
              "article_num":        13,
              "regulation_ref":     "Article 13 — EU AMLR 2024/1624",
              "evidence":           "...",
              "description":        "...",
              "competency":         "Foundational",
              "explainability_trace": {
                  "role": ..., "responsibility": ..., "risk": ...,
                  "control": ..., "regulation": ..., "article_num": ...,
                  "training": ..., "source": "neo4j|rag"
              }
            },
            ...
          ],
          "roadmap": {"Q1": [...], "Q2": [...], "Q3": [...], "Q4": [...]},
          "audit_summary": {...}
        }
    """
    builder = KnowledgeIndexBuilder()
    modules: List[Dict[str, Any]] = []
    seen_modules: set = set()

    # ── 1. Neo4j exact/fuzzy role traversal ───────────────────────────────────
    neo4j_paths = get_governed_paths(role)

    def process_neo4j_path(path):
        reg_ref = _build_regulation_ref(path["regulation"], path["article_num"])
        module_name = generate_module_name(
            role=role,
            responsibility=path["responsibility"],
            risk=path["risk"],
            control=path["control"],
            regulation_ref=reg_ref,
            domain=domain,
        )
        description = _deterministic_description(
            role=role,
            responsibility=path["responsibility"],
            risk=path["risk"],
            control=path["control"],
            regulation_ref=reg_ref,
        )
        local_builder = KnowledgeIndexBuilder()
        evidence = local_builder.assemble_evidence_chain(
            regulation_name=path["regulation"],
            control_name=path["control"],
            limit=2
        )
        return {
            "key": (path["risk"], path["regulation"]),
            "data": {
                "_sort_key":      path["article_num"] or 999,
                "module":         module_name,
                "responsibility": path["responsibility"],
                "risk":           path["risk"],
                "control":        path["control"],
                "regulation":     path["regulation"],
                "article_num":    path["article_num"],
                "regulation_ref": reg_ref,
                "evidence":       evidence,
                "description":    description,
                "source":         "neo4j",
            }
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for path in neo4j_paths:
            key = (path["risk"], path["regulation"])
            if key not in seen_modules:
                seen_modules.add(key)
                futures.append(executor.submit(process_neo4j_path, path))
                
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            modules.append(res["data"])

    # ── 2. Graph lookup for input inherent_risks not yet covered ──────────────
    covered_risks = {m["risk"] for m in modules}
    uncovered_risks = [r for r in inherent_risks if r not in covered_risks]

    if uncovered_risks:
        graph_hits = get_graph_controls_for_risks(uncovered_risks)
        
        def process_graph_hit(hit):
            reg_ref2 = _build_regulation_ref(hit["regulation"], hit["article_num"])
            local_builder = KnowledgeIndexBuilder()
            evidence = local_builder.assemble_evidence_chain(
                regulation_name=hit["regulation"],
                control_name=hit["control"],
                limit=2
            )
            resp = hit.get("responsibility") or _match_responsibility(hit["original_risk"], responsibilities)
            module_name = generate_module_name(
                role=role,
                responsibility=resp,
                risk=hit["matched_risk"],
                control=hit["control"],
                regulation_ref=reg_ref2,
                domain=domain,
            )
            description = generate_module_description(
                role=role,
                responsibility=resp,
                risk=hit["matched_risk"],
                control=hit["control"],
                regulation=hit["regulation"],
                article_num=hit["article_num"],
                evidence=evidence,
                domain=domain,
            )
            return {
                "key": (hit["matched_risk"], hit["regulation"]),
                "data": {
                    "_sort_key":      hit["article_num"] or 999,
                    "module":         module_name,
                    "responsibility": resp,
                    "risk":           hit["matched_risk"],
                    "control":        hit["control"],
                    "regulation":     hit["regulation"],
                    "article_num":    hit["article_num"],
                    "regulation_ref": reg_ref2,
                    "evidence":       evidence,
                    "description":    description,
                    "source":         "neo4j_risk_match",
                }
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for hit in graph_hits:
                key = (hit["matched_risk"], hit["regulation"])
                if key not in seen_modules:
                    seen_modules.add(key)
                    futures.append(executor.submit(process_graph_hit, hit))
                    
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                modules.append(res["data"])
                covered_risks.add(res["data"]["risk"])

    # ── 3. RAG augmentation for risks not in graph at all ─────────────────────
    still_uncovered = [r for r in inherent_risks if r not in covered_risks]
    if still_uncovered or not modules:
        rag_hits = find_regulations_for_risks(
            risks=still_uncovered if still_uncovered else inherent_risks,
            responsibilities=responsibilities,
            limit_per_risk=2,
        )

        def process_rag_hit(hit):
            control = _infer_control_from_regulation(
                risk=hit["risk"],
                regulation=hit["regulation"],
                evidence=hit["evidence_snippet"],
            )
            reg_ref3 = _build_regulation_ref(hit["regulation"], hit["article_num"], hit["recital_num"])
            resp = _match_responsibility(hit["risk"], responsibilities)
            module_name = generate_module_name(
                role=role,
                responsibility=resp,
                risk=hit["risk"],
                control=control,
                regulation_ref=reg_ref3,
                domain=domain,
            )
            description = generate_module_description(
                role=role,
                responsibility=resp,
                risk=hit["risk"],
                control=control,
                regulation=hit["regulation"],
                article_num=hit["article_num"],
                evidence=hit["evidence_snippet"],
                domain=domain,
            )

            return {
                "key": (hit["risk"], hit["regulation"]),
                "data": {
                    "_sort_key":      hit["article_num"] or hit["recital_num"] or 999,
                    "module":         module_name,
                    "responsibility": resp,
                    "risk":           hit["risk"],
                    "control":        control,
                    "regulation":     hit["regulation"],
                    "article_num":    hit["article_num"],
                    "regulation_ref": _build_regulation_ref(hit["regulation"], hit["article_num"], hit["recital_num"]),
                    "evidence":       hit["evidence_snippet"],
                    "description":    description,
                    "source":         "rag",
                }
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for hit in rag_hits:
                key = (hit["risk"], hit["regulation"])
                if key not in seen_modules and hit["legal_type"] != "general":
                    seen_modules.add(key)
                    futures.append(executor.submit(process_rag_hit, hit))
                    
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                modules.append(res["data"])

    # ── 3. Assign competency, sort by progression, assign quarters ──────────────
    # Derive competency for every module
    for mod in modules:
        mod["competency"] = _competency_from_control(mod["control"], mod["regulation"])

    # Sort: Foundational first → Intermediate → Advanced, then by article number
    _comp_order = {"Foundational": 0, "Intermediate": 1, "Advanced": 2}
    modules.sort(key=lambda m: (
        _comp_order.get(m["competency"], 1),
        m["_sort_key"]
    ))

    # Always spread across all 4 quarters regardless of how many modules or
    # what competency they have. Use round-robin over the full sequence so
    # even 5 all-Foundational modules get Q1, Q2, Q3, Q4, Q1.
    _quarter_sequence = [
        "Q1 Foundation",
        "Q2 Application",
        "Q3 Deepening",
        "Q4 Embedding",
    ]
    _quarter_key = {
        "Q1 Foundation":  "Q1",
        "Q2 Application": "Q2",
        "Q3 Deepening":   "Q3",
        "Q4 Embedding":   "Q4",
    }

    roadmap: Dict[str, List[str]] = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    plan: List[Dict[str, Any]] = []

    for idx, mod in enumerate(modules):
        q_label    = _quarter_sequence[idx % 4]
        q_key      = _quarter_key[q_label]
        competency = mod["competency"]

        roadmap[q_key].append(mod["module"])

        plan.append({
            "quarter":          q_label,
            "module":           mod["module"],
            "responsibility":   mod["responsibility"],
            "risk":             mod["risk"],
            "control":          mod["control"],
            "regulation":       mod["regulation"],
            "article_num":      mod["article_num"],
            "regulation_ref":   mod["regulation_ref"],
            "evidence":         mod["evidence"],
            "description":      mod["description"],
            "competency":       competency,
            "explainability_trace": {
                "role":           role,
                "responsibility": mod["responsibility"],
                "risk":           mod["risk"],
                "control":        mod["control"],
                "regulation":     mod["regulation"],
                "article_num":    mod["article_num"],
                "regulation_ref": mod["regulation_ref"],
                "training":       mod["module"],
                "source":         mod["source"],
            }
        })

    # ── 4. Audit summary ──────────────────────────────────────────────────────
    article_refs = sorted(set(
        m["regulation_ref"] for m in plan if m["article_num"] or "Recital" in m["regulation"]
    ))
    audit_summary = {
        "role":              role,
        "total_modules":     len(plan),
        "regulations_cited": article_refs,
        "risks_covered":     sorted(set(m["risk"] for m in plan)),
        "controls_applied":  sorted(set(m["control"] for m in plan)),
        "sources":           sorted(set(m["explainability_trace"]["source"] for m in plan)),
    }

    return {
        "role":          f"{role} ({domain})",
        "plan":          plan,
        "roadmap":       roadmap,
        "audit_summary": audit_summary,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_regulation_ref(regulation: str, article_num: Optional[int],
                           recital_num: Optional[int] = None) -> str:
    if article_num:
        return f"Article {article_num} — EU AMLR 2024/1624"
    if recital_num:
        return f"Recital {recital_num} — EU AMLR 2024/1624"
    return f"{regulation} — EU AMLR 2024/1624"


def _build_module_name(regulation: str, control: str, risk: str) -> str:
    art_m = re.search(r'Article\s+(\d+)', regulation, re.IGNORECASE)
    rec_m = re.search(r'Recital\s+(\d+)', regulation, re.IGNORECASE)
    ref = f"Art.{art_m.group(1)}" if art_m else (f"Rec.{rec_m.group(1)}" if rec_m else regulation[:20])
    return f"{control} — {ref}"


def _match_responsibility(risk: str, responsibilities: List[str]) -> str:
    """Best-effort match: pick the most relevant responsibility for a risk."""
    risk_lower = risk.lower()
    for resp in responsibilities:
        if any(w in resp.lower() for w in risk_lower.split() if len(w) > 4):
            return resp
    return responsibilities[0] if responsibilities else "General Compliance"


def _infer_control_from_regulation(risk: str, regulation: str, evidence: str) -> str:
    """Ask LLM to name the specific AML control required by this regulation.

    Strictly grounded in evidence — no invention allowed.
    """
    prompt = f"""
    Based ONLY on the legal evidence below, state in 2-5 words the specific AML/CFT control
    that an obliged entity must implement to mitigate the risk of '{risk}' under {regulation}.

    Legal Evidence:
    \"\"\"{evidence}\"\"\"

    Reply with the control name only (e.g. "Customer Due Diligence", "Enhanced Due Diligence",
    "Suspicious Activity Reporting"). If the evidence does not specify a control, reply "Compliance Control".
    """
    try:
        return governed_llm_call(prompt).strip().strip('"').strip("'")
    except Exception:
        return "Compliance Control"
