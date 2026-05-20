from app.db.database import engine
from app.models.models import Base
from app.rag.knowledge_index import KnowledgeChunk
from sqlalchemy import text

# Ensure pgvector extension is loaded in the database
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)

print("Database tables created")
