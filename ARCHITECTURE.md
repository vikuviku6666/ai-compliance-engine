# AI Compliance Training Orchestration Engine
## Architecture Overview — Hackathon Documentation

---

## System Purpose

An AI-powered compliance training plan generator for AML (Anti-Money Laundering) roles.

The system takes a **role + responsibilities + inherent risks** as input and produces a **4-quarter training plan** with:
- Article-level EU AMLR 2024/1624 regulation citations
- Full explainability trace per module (Role → Risk → Control → Regulation → Training)
- Audit-safe evidence from real legal text
- Zero hallucination — LLM is strictly constrained to governance data

---

## Core Design Principle

```
The LLM is NOT a compliance decision maker.
The LLM is an AI learning and explainability layer.

Neo4j   = governance brain     (decides what risks, controls, regulations apply)
pgvector = legal memory        (stores real EU AMLR article/recital text)
LLM      = explanation engine  (generates descriptions, grounded in evidence)
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Runtime** | Python 3.12 + UV | Backend package management |
| **API Framework** | FastAPI | REST API |
| **Graph Database** | Neo4j 5 | Governance graph (deterministic compliance mappings) |
| **Relational DB** | PostgreSQL 16 | Training plans, modules, metadata |
| **Vector Store** | pgvector (pg16) | EU AMLR regulation embeddings for RAG |
| **Embeddings** | BAAI/bge-large-en-v1.5 | 1024-dim sentence embeddings via sentence-transformers |
| **LLM** | GPT-4o-mini via OpenRouter | Training descriptions, quiz, simulation (temperature=0) |
| **Frontend** | Next.js 14 + TypeScript | UI |
| **Styling** | Tailwind CSS + shadcn/ui | Component library |
| **Infrastructure** | Docker Compose | PostgreSQL + pgvector + Neo4j |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14)                                          │
│                                                                 │
│  InputSection (Upload.tsx)          page.tsx                    │
│  ├── Role dropdown (live Neo4j)     ├── 4-quarter plan view     │
│  ├── Auto-fill responsibilities     ├── Audit summary panel     │
│  ├── Live risk suggestions          ├── Explainability traces   │
│  └── Custom overrides               ├── Plan quality scorecard  │
│                                     ├── Edit / Approve workflow  │
│                                     └── Saved plans panel       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP (axios)
┌────────────────────────▼────────────────────────────────────────┐
│  Backend (FastAPI)                                              │
│                                                                 │
│  /graph/roles              → Neo4j  (live role list)            │
│  /graph/suggest-risks      → Neo4j + RAG fallback               │
│  /graph/suggest-controls   → Neo4j                              │
│  /graph/regulations        → PostgreSQL (knowledge index)       │
│  /compliance/generate-plan → compliance_engine.py               │
│  /compliance/explainability/{id} → PostgreSQL                   │
│  /workflow/revise/{id}     → LLM revision                       │
│  /workflow/plan/{id}/evaluate → LLM scorecard                   │
└──────┬───────────────────────┬──────────────────────────────────┘
       │                       │
┌──────▼──────┐    ┌───────────▼──────────────────────────────────┐
│   Neo4j 5   │    │  PostgreSQL 16 + pgvector                    │
│             │    │                                              │
│  Governance │    │  Tables:                                     │
│  Graph      │    │  ├── knowledge_chunks (109 EU AMLR chunks)   │
│             │    │  │     └── embedding Vector(1024)            │
│  6 Roles    │    │  ├── training_plans                          │
│  63 Paths   │    │  ├── training_plan_modules                   │
│             │    │  ├── roles, risks, controls, regulations      │
└─────────────┘    └──────────────────────────────────────────────┘
```

---

## Compliance Engine — Primary Flow

```
POST /compliance/generate-plan
  Input: { role, responsibilities[], inherent_risks[] }

       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Neo4j Role Traversal (Deterministic)                  │
│                                                                 │
│  MATCH (Role)-[:HAS_RESPONSIBILITY]->(Responsibility)           │
│       -[:INTRODUCES]->(Risk)                                    │
│       -[:MITIGATED_BY]->(Control)                               │
│       -[:REQUIRED_BY]->(Regulation)                             │
│       -[:TRAINED_BY]->(Training)                                │
│                                                                 │
│  Fuzzy match on role name — works for custom roles too          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Uncovered risks?
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Neo4j Risk-to-Control Match                           │
│                                                                 │
│  For input risks not covered by role traversal,                 │
│  directly fuzzy-match Risk nodes in graph                       │
│  → returns Control + Regulation + Training                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Still uncovered?
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: RAG Augmentation (EU AMLR Knowledge Index)            │
│                                                                 │
│  Hybrid search:                                                 │
│  1. Vector similarity (pgvector cosine distance)                │
│  2. Article/recital number filter (targeted lookup)             │
│  3. Keyword boost + re-ranking                                  │
│                                                                 │
│  LLM infers control name from retrieved evidence text           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Evidence Assembly                                              │
│                                                                 │
│  assemble_evidence_chain(regulation, control)                   │
│  → Returns: [Article X — EU AMLR 2024/1624]\n<real text>       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LLM Description Generation (governed_llm_call)                 │
│                                                                 │
│  Temperature = 0                                                │
│  System prompt = SYSTEM_MENTAL_MODEL (54 rules)                 │
│  Input = evidence text from pgvector                            │
│  Output validated by validate_governance_boundaries()           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  4-Quarter Assignment + Explainability Trace                    │
│                                                                 │
│  Sorted by article number                                       │
│  Q1 Foundation → Q2 Application → Q3 Deepening → Q4 Embedding  │
│                                                                 │
│  Each module carries:                                           │
│  { quarter, module, responsibility, risk, control,              │
│    regulation, article_num, regulation_ref,                     │
│    evidence, description, competency,                           │
│    explainability_trace: {                                      │
│      role → responsibility → risk → control                     │
│      → regulation → article_num → training → source            │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘

  Output: {
    role, plan[], roadmap{Q1-Q4},
    audit_summary: {
      regulations_cited[], risks_covered[],
      controls_applied[], sources[]
    }
  }
```

---

## Neo4j Governance Graph

```
(Role)-[:HAS_RESPONSIBILITY]->(Responsibility)
(Responsibility)-[:INTRODUCES]->(Risk)
(Risk)-[:MITIGATED_BY]->(Control)
(Control)-[:REQUIRED_BY]->(Regulation)
(Control)-[:TRAINED_BY]->(Training)
```

### Graph Stats

| Node Type | Count |
|-----------|-------|
| Roles | 6 |
| Responsibilities | 32 |
| Risks | 25 |
| Controls | 23 |
| Regulations | 17 |
| Training modules | 41 |
| **Total governance paths** | **63** |

### Roles Covered

| Role | Responsibilities | Risks | Paths |
|------|-----------------|-------|-------|
| KYC Analyst | 7 | 12 | 11 |
| Compliance Analyst | 6 | 8 | 8 |
| MLRO | 6 | 6 | 6 |
| AML Investigator | 5 | 5 | 5 |
| Relationship Manager | 5 | 5 | 5 |
| Senior Management | 3 | 3 | 3 |

### Regulations Mapped (sample)

| Regulation | Mapped To |
|-----------|-----------|
| Article 22 | Identity Verification & CDD |
| Article 25 | Ongoing Monitoring & Sanctions |
| Article 32 | EDD, SAR, Risk Assessment |
| Article 43 | PEP Screening |
| Article 46 | PEP Close Associates |
| Article 55 | Beneficial Ownership / UBO |
| Recital 39 | Internal Policy Governance |
| Recital 45 | Staff Training Programmes |
| Recital 78 | Simplified CDD |
| Recital 88 | Case Documentation |

---

## Knowledge Index (pgvector)

- **Source document**: EU AMLR 2024/1624 (Regulation 2024/1624 — 2.3MB PDF)
- **Chunking**: Article/recital boundary-aware, 200–600 chars per chunk
- **Embedding model**: `BAAI/bge-large-en-v1.5` → 1024 dimensions
- **Total chunks**: 109

| Chunk Type | Count |
|-----------|-------|
| Article chunks | 44 |
| Recital chunks | 41 |
| Chapter/General | 24 |

### Search Pipeline

```
Query text
    ↓
1. Embed query (bge-large-en-v1.5)
    ↓
2. Vector similarity (pgvector <-> cosine distance)
   + optional article_num / recital_num filter
    ↓
3. Re-ranking: (1 - distance) + keyword_boost + section_type_boost
    ↓
4. Top-k results with: section, article_num, recital_num, content, relevance
    ↓
5. assemble_evidence_chain → citation-formatted string
   "[Article X — EU AMLR 2024/1624]\n<real text>"
```

---

## LLM Governance Layer

### Mental Model (SYSTEM_MENTAL_MODEL)

Every LLM call in the system is governed by a 54-line system prompt that enforces:

1. **Identity** — "You are NOT a compliance decision maker"
2. **Permitted actions** — explain, summarize, generate training content, quizzes, simulations
3. **Forbidden actions** — invent regulations, risks, controls, governance logic
4. **Governance hierarchy** — LLM NEVER decides Role→Risk→Control→Regulation
5. **Temperature = 0** — deterministic, consistent, audit-safe outputs
6. **Citation rule** — only cite retrieved articles/recitals, never fabricate
7. **Output style** — deterministic, explainable, professional, audit-safe

### Hallucination Guards (validators.py)

| Validator | What it checks |
|-----------|---------------|
| `validate_governance_boundaries()` | Detects governance decision phrases ("you should add training", "this role also requires") and invented domain patterns (blockchain, cybersecurity, AI governance) |
| `validate_no_hallucinated_regulations()` | Extracts Article/Recital references from output; flags any not in the known regulation set |
| `validate_structured_output()` | Schema validation for quiz, simulation, plan, evaluation, role_info outputs |

### governed_llm_call() — Single Gateway

```python
governed_llm_call(
    user_prompt,          # The task
    system_prompt=SYSTEM_MENTAL_MODEL,  # Governance rules
    temperature=0,        # Always deterministic
    response_format={"type": "json_object"}  # Structured output
)
# → validates output → raises GovernanceViolationError if rules broken
```

---

## API Endpoints

### Live Graph & Knowledge

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET` | `/graph/roles` | All roles + responsibilities + risks from Neo4j |
| `GET` | `/graph/role/{name}` | Full governance paths for one role |
| `GET` | `/graph/regulations` | All 85 EU AMLR articles/recitals from knowledge index |
| `POST` | `/graph/suggest-risks` | Suggest risks for given responsibilities (graph + RAG) |
| `POST` | `/graph/suggest-controls` | Controls + regulations for given risks |

### Primary Compliance Engine

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/compliance/generate-plan` | **MAIN** — role + responsibilities + risks → 4-quarter plan |
| `GET` | `/compliance/explainability/{plan_id}` | Full governance chain trace per module |
| `POST` | `/compliance/regulations-for-risks` | Which EU AMLR articles address which risks |

### Training Details

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/generate-training` | Detailed training path with quiz + simulation per module |
| `POST` | `/quiz` | Generate audit-ready quiz for a training module |
| `POST` | `/simulation` | Generate interactive compliance simulation |
| `GET` | `/explainability` | Governance chain by role or training name |

### Plan Management

| Method | Endpoint | Description |
|--------|---------|-------------|
| `GET` | `/workflow/plans` | All saved training plans |
| `GET` | `/workflow/plan/{id}` | Full plan details |
| `POST` | `/workflow/revise/{id}` | Revise plan based on feedback |
| `GET` | `/workflow/plan/{id}/evaluate` | Quality scorecard (3 dimensions) |
| `PATCH` | `/training/plans/{id}` | Update status / reviewer notes |
| `GET` | `/health` | System health check |

---

## Frontend Flow

```
Page Load
    ↓
GET /graph/roles → render 6 role buttons (live from Neo4j)
    ↓
User clicks role
    ↓
Auto-fill responsibilities (from graph data)
Pre-select known risks for that role
    ↓
POST /graph/suggest-risks → render additional risk chips
    ↓
User selects/deselects risks, adds custom ones
    ↓
Click "Generate Training Plan"
    ↓
POST /compliance/generate-plan
    ↓
Show loading overlay (4 steps with progress indicators)
    ↓
Render plan:
  ├── 4-quarter grid (colour-coded columns)
  ├── Article references per module
  ├── Risk theme per module
  ├── Audit Summary (regulations cited, controls applied)
  ├── Explainability Traces (full governance chain)
  ├── Plan Quality Scorecard (3-dimension LLM evaluation)
  └── Approve / Edit Workflow
          ↓ Edit clicked
          ↓ User enters feedback
          ↓ POST /workflow/revise/{id}
          ↓ Full-screen loading overlay (same style)
          ↓ Plan reloaded with GET /workflow/plan/{id}
```

---

## Plan Quality Scorecard

Evaluated by LLM using a strict rubric (no inflated scores):

| Dimension | Weight | Criteria |
|-----------|--------|---------|
| AML Regulation Relevance | 40% | Are specific EU AMLR articles/recitals cited per module? |
| Role Alignment | 30% | Are modules directly applicable to the role's daily duties? |
| Risk & Control Coverage | 30% | Does every input risk have a training module with a control? |

Score ranges: `0–29 = Poor`, `30–49 = Weak`, `50–69 = Fair`, `70–89 = Good`, `90–100 = Excellent`

```
Overall = (AML_Relevance × 0.4) + (Role_Alignment × 0.3) + (Risk_Coverage × 0.3)
```

---

## Docker Compose Services

```yaml
postgres:  pgvector/pgvector:pg16  → port 5432  (compliance DB + vector store)
neo4j:     neo4j:5                 → port 7474/7687  (governance graph)
```

Backend and frontend run locally (not containerised).

---

## Running the System

```bash
# Start infrastructure
docker compose up -d

# Terminal 1 — Backend (from project root)
compliance-api
# = lsof -ti :8000 | xargs kill -9; uv run python -m uvicorn app.main:app --app-dir backend --reload

# Terminal 2 — Frontend
compliance-ui
# = cd frontend/my-app && npm run dev

# Seed graph (first time only)
cd backend && PYTHONPATH=. uv run python app/graph/seed_graph.py

# Re-index EU AMLR PDF (first time only)
cd backend && uv run python -c "
from app.rag.knowledge_index import KnowledgeIndexBuilder
b = KnowledgeIndexBuilder()
b.create_tables()
b.index_document('data/documents/compliance/eu_amlr_1624.pdf', drop_existing=True)
"
```

---

## File Structure

```
ai-compliance-engine/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes.py              — 18 REST endpoints
│       ├── services/
│       │   ├── compliance_engine.py   — PRIMARY: 3-layer plan builder
│       │   ├── llm_service.py         — governed_llm_call + SYSTEM_MENTAL_MODEL
│       │   ├── validators.py          — 3 hallucination guards
│       │   ├── roadmap_service.py     — Neo4j traversal + evidence retrieval
│       │   ├── quiz_service.py        — LLM quiz generation
│       │   ├── simulation_service.py  — LLM simulation generation
│       │   └── generator.py           — Plan generation + evaluation + revision
│       ├── graph/
│       │   ├── neo4j_client.py        — Neo4j driver singleton
│       │   ├── seed_graph.py          — 6 roles, 63 paths (idempotent MERGE)
│       │   ├── setup_graph.py         — Original basic seed
│       │   └── create_relationships.py
│       ├── rag/
│       │   ├── knowledge_index.py     — Hybrid search + evidence chain
│       │   ├── document_parser.py     — Article/recital boundary chunker
│       │   ├── embedder.py            — bge-large-en-v1.5 (1024-dim)
│       │   └── llm_content.py         — RAG-based content helpers
│       ├── db/
│       │   └── database.py            — SQLAlchemy engine + session
│       ├── models/
│       │   └── models.py              — ORM: TrainingPlan, TrainingPlanModule, etc.
│       └── main.py                    — FastAPI app + CORS
├── frontend/
│   └── my-app/
│       ├── app/
│       │   └── page.tsx               — Main page + normalise() + plan view
│       └── components/
│           ├── Upload.tsx             — 3-step live input form
│           ├── ApprovalWorkflow.tsx   — Edit/approve with loading overlay
│           ├── PlanScorecard.tsx      — Quality scorecard with ring chart
│           └── SavedPlansPanel.tsx    — Saved plans history
├── docker-compose.yml                 — postgres + neo4j
└── .env                               — API keys + DB connection strings
```

---

## Key Design Decisions

| Decision | Rationale |
|---------|----------|
| **Neo4j for governance, not LLM** | Compliance mappings must be deterministic and auditable. No LLM decides what risks or controls apply. |
| **temperature=0 everywhere** | Consistent, repeatable outputs for audit purposes |
| **3-layer fallback** | Neo4j role path → Neo4j risk match → RAG — ensures maximum coverage without hallucination |
| **Evidence chain per module** | Every training module traces back to real EU AMLR article/recital text |
| **Validators after every LLM call** | Catches governance boundary violations before they reach the user |
| **Structured output (JSON mode)** | Eliminates fragile markdown JSON parsing; API-level schema enforcement |
| **Hybrid vector search** | Pure cosine similarity misses exact article references; keyword boost + section type boost fixes precision |

---

*Last updated: 2026-05-19*
*EU AMLR 2024/1624 — Regulation (EU) 2024/1624 of the European Parliament and of the Council*
