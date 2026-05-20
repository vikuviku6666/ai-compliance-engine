import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables exist and warm up the embedding model.
    Moves table creation and model cold-start to server boot time.
    """
    try:
        from app.db.database import engine
        from app.models.models import Base
        from app.rag.knowledge_index import KnowledgeChunk
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables verified/created")
    except Exception as e:
        print(f"⚠ Database table creation failed (non-fatal): {e}")

    try:
        from app.rag.embedder import create_embedding
        create_embedding("warmup")
        print("✓ Embedding model warmed up")
    except Exception as e:
        print(f"⚠ Warmup failed (non-fatal): {e}")
    yield


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
    return {"status": "running"}