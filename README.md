# Vidda Solutions - AI Compliance Engine

**[📺 Watch the Demo Video](https://youtu.be/skAk-YrqJyc)**

An enterprise-grade, deterministic AI compliance training orchestration engine. Vidda takes raw corporate job descriptions (via PDF or text), traverses a pre-mapped governance graph, searches EU AMLR regulatory vectors, and generates mathematically proven, audit-ready training paths ready for LMS export.

## 🚀 Key Features

* **Instant Corporate Parsing**: Upload a department charter PDF; the system extracts multiple roles, their core responsibilities, and their inherent financial crime risks.
* **Deterministic Governance Engine**: Uses **Neo4j** to strictly map `Role → Responsibility → Risk → Mitigating Control`. No LLM hallucinations.
* **RAG Legal Memory**: Uses **pgvector** to query the exact text of the EU AMLR 2024/1624 regulation to back up every control.
* **Extreme Explainability**: Every generated training module comes with a transparent logic trace and an explicit legal evidence snippet for regulators.
* **Massive Concurrency**: A ThreadPool architecture generates parallel training paths for multiple roles simultaneously.
* **LMS Ready**: 1-click generation and approval creates a structured JSON payload ready to be ingested by Workday, SAP Litmos, Cornerstone, etc.

## 🧠 How it Works: Generating a Plan from a Role

When you provide a job role and its responsibilities on the platform, the engine executes a three-phase deterministic pipeline:

### 1. Extraction Phase
*   **LLM Parsing:** Raw text (or PDF content) is sent to the backend. An LLM parses the unstructured text into a structured JSON payload containing the **Role Name**, **Responsibilities**, and implied **Inherent Risks**.
*   **Graph Authority Override:** The system queries the Neo4j Governance Graph. If the role exists, the engine overrides the LLM-generated risks with the authoritative, pre-approved risks from the database to strictly enforce compliance standards.

### 2. Compliance Engine Processing
The validated data is passed to the core compliance engine for a multi-step orchestration:
*   **Step A: Deterministic Graph Traversal:** The engine queries Neo4j using the role to traverse hardcoded governance paths, mapping: `Role → Responsibility → Risk → Mitigating Control → Regulation → Training Module`.
*   **Step B: Risk Augmentation:** For custom risks not covered in the direct traversal, the graph is queried in reverse, starting from the *Risk* to find associated controls and regulations.
*   **Step C: RAG Legal Fallback:** For risks with no graph coverage, a vector search runs against PostgreSQL. It queries a Knowledge Index of the **EU AMLR 2024/1624**. An LLM reads the exact retrieved legal articles and infers the required mitigating control.

### 3. Plan Generation & Display
With all regulatory requirements mapped, the final curriculum is assembled:
*   **Grounded Descriptions:** An LLM generates a professional module title and description, strictly constrained by the retrieved legal evidence to ensure audit-safety.
*   **Competency Assignment:** Controls are evaluated to assign competency levels (e.g., standard KYC is "Foundational", while SAR reporting is "Advanced").
*   **Quarterly Roadmap:** Modules are sorted by competency and legal article number, then distributed across a 4-quarter roadmap using round-robin distribution.
*   **Explainability Trace:** Every module saves a complete audit trail (the "Explainability Trace") to the database, proving the exact path from Role to EU AMLR Article.
*   **UI Rendering:** The structured JSON is sent to the frontend, rendering the dashboard scorecards, the quarterly roadmap, and the explainability tooltips.

## 🏗️ Architecture

Read the full deep-dive in `ARCHITECTURE.md`.

* **Backend**: Python 3.12, FastAPI, OpenAI GPT-4o-mini (for generation constrained strictly by evidence context).
* **Databases**: Neo4j (Governance Graph), PostgreSQL 16 + pgvector (Relational metadata + EU AMLR Vector Embeddings).
* **Frontend**: Next.js 14, Tailwind CSS, Shadcn UI.

## 🛠️ Local Development Setup

### 1. Requirements
* Docker Desktop (for Postgres/pgvector and Neo4j)
* Python 3.12+ (Use `uv` for lightning-fast package management)
* Node.js v20+

### 2. Start the Databases
```bash
docker-compose up -d
```
*(This starts PostgreSQL on port 5432 and Neo4j on ports 7474/7687)*

### 3. Setup the Backend
```bash
# Create and activate a virtual environment
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Copy environment variables and set your OpenAI API key
cp .env.example .env
```
Once `.env` is configured, seed the database with the EU AMLR knowledge and graph logic:
```bash
python backend/app/main.py
```
*(The FastAPI server will boot up and handle the cold-start DB creations automatically).*

### 4. Start the Frontend
```bash
cd frontend/my-app
npm install
npm run dev
```

The application is now running at `http://localhost:3000`.

## 📜 Repository Structure
* `/backend`: FastAPI Python server, services, and db models.
* `/frontend`: Next.js React application.
* `/pitch_script.md`: The 3-minute hackathon demo script.
* `/Vidda Solutions Learning Program Generation...pdf`: Hackathon background context.

## 💾 LMS Integration
When a curriculum is approved, you can instantly export the payload via the UI or by hitting:
`GET /training/plans/{plan_id}/export`

It will return a heavily-structured JSON document containing the roles, 4-quarter path, mapping taxonomy, and exact EU AMLR governance traces.
