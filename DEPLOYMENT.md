# GCP Deployment Guide (Including Databases)

This guide explains how to deploy the AI Compliance Engine entirely on Google Cloud Platform (GCP).

## 1. Database Architecture on GCP

Since the application requires PostgreSQL (with `pgvector`) and Neo4j, you have two primary paths on GCP:

### Option A: Fully Managed (Recommended for production)
*   **PostgreSQL:** Use **Google Cloud SQL for PostgreSQL**. It natively supports the `pgvector` extension.
*   **Neo4j:** Use **Neo4j AuraDB Free Tier** (hosted on GCP). It is managed by Neo4j and requires zero DevOps.

### Option B: Self-Hosted on Compute Engine (Cheapest, requires Docker)
*   Deploy a single **e2-micro or e2-small Google Compute Engine (VM)**.
*   Install Docker and run your existing `docker-compose.yml` exactly as you do locally.

---

## 2. Deploying Option A (Fully Managed Cloud)

### Step 1: Set up Cloud SQL (PostgreSQL)
1. Go to GCP Console -> SQL -> Create Instance -> Choose PostgreSQL (Version 15 or 16).
2. Set a password for the `postgres` user.
3. Once created, note the **Public IP Address**.
4. (Optional but recommended) In the Connections tab, add your IP or allow `0.0.0.0/0` temporarily to seed it, or use the Cloud SQL Auth Proxy.
5. Connect to it and run `CREATE DATABASE compliance;`

### Step 2: Set up Neo4j AuraDB
1. Go to [Neo4j Aura](https://neo4j.com/cloud/platform/aura-graph-database/).
2. Create a Free Instance (hosted on GCP).
3. Download the `.txt` file containing your generated password and `neo4j+s://` URI.

### Step 3: Deploy Backend to Cloud Run
Run this from the project root:

```bash
gcloud run deploy vidda-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="OPENAI_API_KEY=your-key,\
NEO4J_URI=neo4j+s://YOUR_AURA_DB_ID.databases.neo4j.io,\
NEO4J_USER=neo4j,\
NEO4J_PASSWORD=your_aura_password,\
DATABASE_URL=postgresql://postgres:your_cloudsql_password@YOUR_CLOUDSQL_IP:5432/compliance"
```
*Note: Make sure your `app/db/database.py` and `app/graph/neo4j_client.py` respect these environment variables (they usually default to localhost if not set).*

### Step 4: Seed the Databases
Once the backend is live, you must seed the Cloud SQL and AuraDB databases.
From your local machine (pointing to the live databases):
```bash
export NEO4J_URI=neo4j+s://YOUR_AURA_DB_ID.databases.neo4j.io
export NEO4J_PASSWORD=your_aura_password
export DATABASE_URL=postgresql://postgres:your_cloudsql_password@YOUR_CLOUDSQL_IP:5432/compliance

# Seed Neo4j Governance Graph
uv run python backend/app/graph/seed_graph.py

# Boot backend locally once just to trigger the Postgres Vector tables creation
uv run python backend/app/main.py
```

### Step 5: Deploy Frontend to Cloud Run
Run this from the `frontend/my-app` directory:

```bash
# Get the backend URL from Step 3 (e.g., https://vidda-backend-xyz.run.app)
gcloud run deploy vidda-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-build-env-vars NEXT_PUBLIC_API_URL=https://vidda-backend-xyz.run.app
```

---

## 3. Deploying Option B (Compute Engine VM)

If you want the cheapest possible setup that perfectly mirrors your local environment:

1. Create a **Google Compute Engine** instance (Ubuntu, e2-medium).
2. Open Firewall ports for 3000 (Frontend), 8000 (Backend).
3. SSH into the VM:
   ```bash
   sudo apt update && sudo apt install docker.io docker-compose git -y
   git clone <your-repo-url>
   cd ai-compliance-engine
   ```
4. Configure `.env` with your OpenAI Key.
5. Start the databases:
   ```bash
   sudo docker-compose up -d
   ```
6. Build and start the backend and frontend using the Dockerfiles we generated.
