# Vidda Solutions - AI Compliance Engine

**[📺 Watch the Demo Video](https://youtu.be/k3GOkezhGdk)**

An enterprise-grade, deterministic AI compliance training orchestration engine. Vidda takes raw corporate job descriptions (via PDF or text), traverses a pre-mapped governance graph, searches EU AMLR regulatory vectors, and generates mathematically proven, audit-ready training paths ready for LMS export.

## 🚀 Key Features

* **Instant Corporate Parsing**: Upload a department charter PDF; the system extracts multiple roles, their core responsibilities, and their inherent financial crime risks.
* **Deterministic Governance Engine**: Uses **Neo4j** to strictly map `Role → Responsibility → Risk → Mitigating Control`. No LLM hallucinations.
* **RAG Legal Memory**: Uses **pgvector** to query the exact text of the EU AMLR 2024/1624 regulation to back up every control.
* **Extreme Explainability**: Every generated training module comes with a transparent logic trace and an explicit legal evidence snippet for regulators.
* **Massive Concurrency**: A ThreadPool architecture generates parallel training paths for multiple roles simultaneously.
* **LMS Ready**: 1-click generation and approval creates a structured JSON payload ready to be ingested by Workday, SAP Litmos, Cornerstone, etc.

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
