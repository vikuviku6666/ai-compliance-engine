import sys
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

APP_VERSION = "1.0.0"
DB_VERSION = "1.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables exist, warm up the embedding model, and initialize Neo4j.
    Moves table creation and model cold-start to server boot time.
    """
    try:
        from app.db.database import engine, SessionLocal
        from app.models.models import Base, SystemMetadata
        from app.rag.knowledge_index import KnowledgeChunk
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        
        # Initialize/Update Database Version
        try:
            with SessionLocal() as db:
                meta = db.query(SystemMetadata).filter_by(key="db_version").first()
                if not meta:
                    db.add(SystemMetadata(key="db_version", value=DB_VERSION, updated_at=datetime.now().isoformat()))
                else:
                    meta.value = DB_VERSION
                    meta.updated_at = datetime.now().isoformat()
                db.commit()
        except Exception as meta_err:
            print(f"⚠ Could not update DB metadata: {meta_err}")

        print("✓ Database tables verified/created")
    except Exception as e:
        print(f"⚠ Database table creation failed (non-fatal): {e}")

    try:
        from app.rag.embedder import create_embedding
        create_embedding("warmup")
        print("✓ Embedding model warmed up")
    except Exception as e:
        print(f"⚠ Warmup failed (non-fatal): {e}")

    try:
        from app.graph.neo4j_client import _driver_instance
        _driver_instance.connect()
        health = _driver_instance.health_check()
        if health["connected"]:
            print(f"✓ Neo4j connected (version: {health.get('version', 'unknown')})")
        else:
            print(f"⚠ Neo4j health check failed: {health.get('error', 'unknown')}")
    except Exception as e:
        print(f"⚠ Neo4j initialization failed (non-fatal): {e}")

    yield

    try:
        from app.graph.neo4j_client import close_driver
        close_driver()
        print("✓ Neo4j driver closed")
    except Exception as e:
        print(f"⚠ Neo4j shutdown error: {e}")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def health():
    return {
        "status": "running",
        "version": APP_VERSION
    }


@app.get("/health/detailed")
def health_detailed():
    """Detailed health check including Neo4j and PostgreSQL."""
    from app.graph.neo4j_client import health_check as neo4j_health
    from app.db.database import engine, SessionLocal
    from app.models.models import SystemMetadata
    from sqlalchemy import text

    health_status = {
        "service": "running",
        "version": APP_VERSION,
        "db_version": "unknown",
        "neo4j": neo4j_health(),
        "postgresql": {"connected": False, "error": None},
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            health_status["postgresql"] = {"connected": True}
        
        with SessionLocal() as db:
            meta = db.query(SystemMetadata).filter_by(key="db_version").first()
            if meta:
                health_status["db_version"] = meta.value
    except Exception as e:
        health_status["postgresql"]["error"] = str(e)

    overall_status = (
        "healthy"
        if health_status["neo4j"]["connected"]
        and health_status["postgresql"]["connected"]
        else "degraded"
    )
    health_status["overall"] = overall_status

    return health_status
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
