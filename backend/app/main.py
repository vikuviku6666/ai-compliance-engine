import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the embedding model before any user request arrives.
    Moves the 1.5s cold-start cost to server boot time, not first click.
    """
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