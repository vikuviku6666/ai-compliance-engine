"""
Knowledge Index Builder — Phase 5 upgrade

Changes vs Phase 2.1:
- Stores article_num, recital_num, chapter, legal_type per chunk
- Hybrid retrieval: vector similarity + keyword (ILIKE) + Neo4j graph
- Re-ranking: scores by distance + section match boost
- Evidence chain assembler for audit-grade context
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.rag.document_parser import DocumentParser, DocumentChunk
from app.rag.embedder import create_embedding
from app.db.database import SessionLocal
from app.graph.neo4j_client import driver
from sqlalchemy import text, Column, String, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from typing import List, Optional
from datetime import datetime
import re

from app.db.database import Base


class KnowledgeChunk(Base):
    """Store document chunks with embeddings and legal metadata in PostgreSQL."""
    __tablename__ = "knowledge_chunks"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id      = Column(String, unique=True, index=True)
    source        = Column(String, index=True)
    section       = Column(String, index=True)          # "Article 13", "Recital 40"
    subsection    = Column(String, nullable=True)
    # --- Phase 5 metadata ---
    article_num   = Column(Integer, nullable=True, index=True)
    recital_num   = Column(Integer, nullable=True, index=True)
    chapter       = Column(String, nullable=True)
    legal_type    = Column(String, default="general")   # article | recital | chapter | general
    # --- AML metadata ---
    topic           = Column(String, nullable=True, index=True)
    obligation_type = Column(String, nullable=True, index=True)
    actor           = Column(String, nullable=True)
    jurisdiction    = Column(String, nullable=True, default="EU")
    risk_category   = Column(String, nullable=True, index=True)
    # -------------------------
    content       = Column(String)
    embedding     = Column(Vector(1024))
    embedding_model = Column(String, default="BAAI/bge-large-en-v1.5")
    created_at    = Column(String)


class KnowledgeIndexBuilder:
    """Build and query the compliance knowledge index."""

    def __init__(self):
        self.parser = DocumentParser(min_chunk_size=200, max_chunk_size=600)
        self.db = SessionLocal()

    # ──────────────────────────────────────────────────────────────────────────
    # Schema management
    # ──────────────────────────────────────────────────────────────────────────

    def create_tables(self):
        """Create / migrate knowledge_chunks table."""
        from app.db.database import engine
        # Add new columns if they don't exist (safe migration)
        with engine.connect() as conn:
            for col, defn in [
                ("article_num", "INTEGER"),
                ("recital_num", "INTEGER"),
                ("chapter",     "VARCHAR"),
                ("legal_type",  "VARCHAR DEFAULT 'general'"),
                ("topic",       "VARCHAR"),
                ("obligation_type", "VARCHAR"),
                ("actor",       "VARCHAR"),
                ("jurisdiction", "VARCHAR DEFAULT 'EU'"),
                ("risk_category", "VARCHAR"),
            ]:
                try:
                    conn.execute(text(
                        f"ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS {col} {defn}"
                    ))
                    conn.commit()
                except Exception:
                    conn.rollback()
        Base.metadata.create_all(bind=engine)
        print("✓ knowledge_chunks table ready")

    def drop_and_recreate(self):
        """Drop and recreate table — use only when re-indexing from scratch."""
        from app.db.database import engine
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS knowledge_chunks CASCADE"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        print("✓ knowledge_chunks dropped and recreated")

    # ──────────────────────────────────────────────────────────────────────────
    # Indexing
    # ──────────────────────────────────────────────────────────────────────────

    def index_document(self, file_path: str, source_name: str = "EU_AMLR_1624",
                       drop_existing: bool = False) -> dict:
        """Parse document and build knowledge index with rich metadata.

        Args:
            file_path:      Path to PDF or HTML file
            source_name:    Identifier stored on every chunk
            drop_existing:  If True, drops all existing chunks for this source first
        """
        print(f"\n📄 Indexing: {source_name}")

        if drop_existing:
            self.db.execute(
                text("DELETE FROM knowledge_chunks WHERE source = :src"),
                {"src": source_name}
            )
            self.db.commit()
            print(f"  ✓ Cleared existing chunks for {source_name}")

        print("  • Parsing document…")
        chunks = self.parser.parse_document(file_path, source_name)
        print(f"  ✓ {len(chunks)} chunks extracted")

        # Stats
        art_chunks = sum(1 for c in chunks if c.article_num is not None)
        rec_chunks = sum(1 for c in chunks if c.recital_num is not None)
        print(f"    ├─ Article chunks : {art_chunks}")
        print(f"    ├─ Recital chunks : {rec_chunks}")
        print(f"    └─ General chunks : {len(chunks) - art_chunks - rec_chunks}")

        print("  • Generating embeddings…")
        stored = skipped = errors = 0

        for i, chunk in enumerate(chunks):
            try:
                existing = self.db.execute(
                    text("SELECT 1 FROM knowledge_chunks WHERE chunk_id = :cid"),
                    {"cid": chunk.chunk_id}
                ).fetchone()
                if existing:
                    skipped += 1
                    continue

                emb = create_embedding(chunk.content)

                kc = KnowledgeChunk(
                    chunk_id      = chunk.chunk_id,
                    source        = chunk.source,
                    section       = chunk.section,
                    subsection    = chunk.subsection,
                    article_num   = chunk.article_num,
                    recital_num   = chunk.recital_num,
                    chapter       = chunk.chapter,
                    legal_type    = chunk.legal_type,
                    topic           = chunk.topic,
                    obligation_type = chunk.obligation_type,
                    actor           = chunk.actor,
                    jurisdiction    = chunk.jurisdiction,
                    risk_category   = chunk.risk_category,
                    content       = chunk.content[:5000],
                    embedding     = emb,
                    created_at    = datetime.now().isoformat(),
                )
                self.db.add(kc)
                stored += 1

                if stored % 20 == 0:
                    self.db.commit()
                    print(f"    … {i + 1}/{len(chunks)} chunks processed")

            except Exception as e:
                errors += 1
                print(f"  ⚠ Error on chunk {i}: {e}")
                self.db.rollback()

        self.db.commit()
        print(f"  ✓ stored={stored}  skipped={skipped}  errors={errors}")

        # Dynamically link each Recital to its closest Article via pgvector similarity
        self.link_recitals_to_articles()

        # Update Neo4j with richer section nodes
        self._update_neo4j_index(chunks, source_name, drop_existing)

        return {
            "source":         source_name,
            "chunks_parsed":  len(chunks),
            "chunks_stored":  stored,
            "chunks_skipped": skipped,
            "chunks_errors":  errors,
            "status":         "success",
        }

    def _update_neo4j_index(self, chunks: List[DocumentChunk],
                             source_name: str, replace: bool = False):
        """Keep Neo4j in sync with article/recital nodes."""
        with driver.session() as session:
            if replace:
                session.run(
                    "MATCH (d:Document {source: $src}) DETACH DELETE d",
                    src=source_name
                )

            # Upsert document node
            session.run(
                """
                MERGE (d:Document {source: $source})
                SET d.name = $name, d.updated_at = datetime()
                """,
                source=source_name,
                name="EU AMLR 2024/1624"
            )

            # Upsert section nodes keyed by (source, section)
            seen: set = set()
            for chunk in chunks:
                key = (chunk.source, chunk.section)
                if key in seen:
                    continue
                seen.add(key)
                session.run(
                    """
                    MERGE (s:Section {source: $source, name: $section})
                    SET s.legal_type  = $legal_type,
                        s.article_num = $article_num,
                        s.recital_num = $recital_num,
                        s.chapter     = $chapter
                    WITH s
                    MATCH (d:Document {source: $source})
                    MERGE (d)-[:HAS_SECTION]->(s)
                    """,
                    source     = chunk.source,
                    section    = chunk.section,
                    legal_type = chunk.legal_type,
                    article_num= chunk.article_num,
                    recital_num= chunk.recital_num,
                    chapter    = chunk.chapter or "",
                )

        print(f"  ✓ Neo4j updated — {len(seen)} section nodes")

    def link_recitals_to_articles(self):
        """Dynamically link each Recital to its semantically closest Article using pgvector similarity."""
        print("  • Dynamically linking Recitals to Articles via pgvector similarity...")
        recitals = self.db.execute(text(
            "SELECT id, embedding FROM knowledge_chunks WHERE legal_type = 'recital'"
        )).fetchall()

        linked = 0
        for r in recitals:
            closest_article = self.db.execute(text("""
                SELECT article_num FROM knowledge_chunks
                WHERE legal_type = 'article' AND article_num IS NOT NULL
                ORDER BY embedding <-> :emb LIMIT 1
            """), {"emb": r.embedding}).scalar()

            if closest_article:
                self.db.execute(text("""
                    UPDATE knowledge_chunks
                    SET article_num = :art_num
                    WHERE id = :rid
                """), {"art_num": closest_article, "rid": r.id})
                linked += 1

        self.db.commit()
        print(f"  ✓ Dynamically linked {linked} Recitals to their most related Articles.")

    # ──────────────────────────────────────────────────────────────────────────
    # Hybrid search (Phase 5.3 + 5.4)
    # ──────────────────────────────────────────────────────────────────────────

    def search(self, query_text: str, limit: int = 5,
               article_num: Optional[int] = None,
               recital_num: Optional[int] = None,
               legal_type: Optional[str] = None,
               obligation_type: Optional[str] = None,
               risk_category: Optional[str] = None,
               actor: Optional[str] = None) -> List[dict]:
        """Hybrid search: vector similarity + optional filters + re-ranking.

        Args:
            query_text:  Free-text query
            limit:       Number of results after re-ranking
            article_num: Optionally restrict to a specific article number
            recital_num: Optionally restrict to a specific recital number
            legal_type:  Optionally restrict to 'article' or 'recital'
            obligation_type: Optionally restrict to 'SHALL', 'MUST', etc.
            risk_category: Optionally restrict to 'KYC', 'Sanctions', etc.
            actor:       Optionally restrict to 'Obliged Entity', etc.

        Returns:
            List of result dicts sorted by relevance score (descending).
        """
        query_emb = create_embedding(query_text)
        query_lower = query_text.lower()

        # ── 1. Vector similarity (top 20 candidates) ──────────────────────────
        base_sql = """
            SELECT
                chunk_id, source, section, subsection,
                article_num, recital_num, chapter, legal_type,
                topic, obligation_type, actor, jurisdiction, risk_category,
                content,
                embedding <-> CAST(:emb AS vector) AS distance
            FROM knowledge_chunks
            WHERE 1=1
        """
        params: dict = {"emb": query_emb, "limit": limit * 4}

        if article_num is not None:
            base_sql += " AND article_num = :art"
            params["art"] = article_num
        elif recital_num is not None:
            base_sql += " AND recital_num = :rec"
            params["rec"] = recital_num

        if legal_type is not None:
            base_sql += " AND legal_type = :ltype"
            params["ltype"] = legal_type

        if obligation_type is not None:
            base_sql += " AND obligation_type = :otype"
            params["otype"] = obligation_type

        if risk_category is not None:
            base_sql += " AND risk_category = :rcat"
            params["rcat"] = risk_category

        if actor is not None:
            base_sql += " AND actor = :actor"
            params["actor"] = actor

        base_sql += " ORDER BY distance LIMIT :limit"

        rows = self.db.execute(text(base_sql), params).fetchall()

        # ── 2. Keyword boost (re-ranking) ──────────────────────────────────────
        results = []
        for row in rows:
            content_lower = row.content.lower()
            distance = float(row.distance)

            # Boost for keyword presence
            keyword_score = sum(
                1 for kw in query_lower.split()
                if len(kw) > 3 and kw in content_lower
            )

            # Boost for article/recital sections (not "General")
            section_boost = 0.05 if row.legal_type in ("article", "recital") else 0

            # Final relevance score: lower distance = better; keyword/section add boost
            relevance = (1 - distance) + (keyword_score * 0.02) + section_boost

            results.append({
                "chunk_id":   row.chunk_id,
                "source":     row.source,
                "section":    row.section,
                "subsection": row.subsection,
                "article_num": row.article_num,
                "recital_num": row.recital_num,
                "chapter":    row.chapter,
                "legal_type": row.legal_type,
                "topic":      row.topic,
                "obligation_type": row.obligation_type,
                "actor":      row.actor,
                "jurisdiction": row.jurisdiction,
                "risk_category": row.risk_category,
                "content":    row.content[:600] + ("…" if len(row.content) > 600 else ""),
                "distance":   round(distance, 4),
                "relevance":  round(relevance, 4),
            })

        # Sort by relevance descending, take top `limit`
        results.sort(key=lambda r: r["relevance"], reverse=True)
        return results[:limit]

    def search_for_answer_type(self, query: str, answer_type: str, limit: int = 3) -> List[dict]:
        """Retrieve deterministic (Articles) vs explanatory (Recitals) content.

        Args:
            query:       Free-text query
            answer_type: "deterministic" (Article) or "explanatory" (Recital)
            limit:       Number of results

        Returns:
            List of result dicts
        """
        if answer_type == "deterministic":
            # For deterministic, we specifically want Articles containing obligations (SHALL/MUST)
            return self.search(
                query_text=query,
                limit=limit,
                legal_type="article",
                obligation_type="SHALL"
            )
        elif answer_type == "explanatory":
            # For explanatory, we specifically want Recitals
            return self.search(
                query_text=query,
                limit=limit,
                legal_type="recital"
            )
        else:
            return self.search(query_text=query, limit=limit)

    def search_by_regulation(self, regulation_name: str, limit: int = 3) -> List[dict]:
        """Search specifically for a regulation reference (article or recital).

        Parses "Article 13", "Recital 40", "Recital 40" etc. from the name
        and does a targeted lookup first, falling back to semantic search.
        """
        # Try to parse article/recital number from the name
        art_match = re.search(r'article\s+(\d+)', regulation_name, re.IGNORECASE)
        rec_match = re.search(r'recital\s+(\d+)', regulation_name, re.IGNORECASE)

        if art_match:
            results = self.search(regulation_name, limit=limit,
                                  article_num=int(art_match.group(1)))
            if results:
                return results

        if rec_match:
            results = self.search(regulation_name, limit=limit,
                                  recital_num=int(rec_match.group(1)))
            if results:
                return results

        # Keyword fallback via ILIKE
        try:
            like_q = f"%{regulation_name.lower().strip()}%"
            rows = self.db.execute(
                text("""
                    SELECT chunk_id, source, section, article_num, recital_num,
                           legal_type, content
                    FROM knowledge_chunks
                    WHERE LOWER(section) LIKE :q OR LOWER(content) LIKE :q
                    LIMIT :lim
                """),
                {"q": like_q, "lim": limit}
            ).fetchall()
            if rows:
                return [
                    {
                        "chunk_id":   r.chunk_id,
                        "source":     r.source,
                        "section":    r.section,
                        "article_num": r.article_num,
                        "recital_num": r.recital_num,
                        "legal_type": r.legal_type,
                        "content":    r.content[:600],
                        "distance":   0.0,
                        "relevance":  1.0,
                    }
                    for r in rows
                ]
        except Exception:
            pass

        # Final fallback: pure vector
        return self.search(regulation_name, limit=limit)

    # ──────────────────────────────────────────────────────────────────────────
    # Evidence chain assembler (Phase 5.5)
    # ──────────────────────────────────────────────────────────────────────────

    def assemble_evidence_chain(self, regulation_name: str,
                                 control_name: str = "",
                                 limit: int = 3) -> str:
        """Assemble an audit-grade evidence chain string.

        Combines targeted regulation lookup + control-keyword search,
        deduplicates, and formats with source citations.

        Returns:
            Formatted string ready to be injected into LLM prompts.
        """
        # 1. Targeted regulation search
        reg_results = self.search_by_regulation(regulation_name, limit=limit)

        # 2. Control keyword search (optional)
        ctrl_results = []
        if control_name:
            ctrl_results = self.search(control_name, limit=2)

        # 3. Deduplicate by chunk_id
        seen: set = set()
        combined: List[dict] = []
        for r in reg_results + ctrl_results:
            if r["chunk_id"] not in seen:
                seen.add(r["chunk_id"])
                combined.append(r)

        if not combined:
            return "Regulatory text not available in the knowledge index."

        # 4. Format with citations
        parts = []
        for r in combined[:limit + 1]:
            citation = r["section"]
            if r["article_num"]:
                citation = f"Article {r['article_num']} — EU AMLR 2024/1624"
            elif r["recital_num"]:
                citation = f"Recital {r['recital_num']} — EU AMLR 2024/1624"
            parts.append(f"[{citation}]\n{r['content']}")

        return "\n\n".join(parts)

    # ──────────────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return index statistics."""
        total   = self.db.execute(text("SELECT COUNT(*) FROM knowledge_chunks")).scalar()
        sources = self.db.execute(text("SELECT COUNT(DISTINCT source) FROM knowledge_chunks")).scalar()
        articles = self.db.execute(
            text("SELECT COUNT(*) FROM knowledge_chunks WHERE article_num IS NOT NULL")
        ).scalar()
        recitals = self.db.execute(
            text("SELECT COUNT(*) FROM knowledge_chunks WHERE recital_num IS NOT NULL")
        ).scalar()

        return {
            "total_chunks":   total,
            "article_chunks": articles,
            "recital_chunks": recitals,
            "general_chunks": total - articles - recitals,
            "sources":        sources,
            "status":         "ready" if total > 0 else "empty",
        }


def main():
    builder = KnowledgeIndexBuilder()
    builder.create_tables()

    pdf_path  = "backend/data/documents/compliance/eu_amlr_1624.pdf"
    html_path = "backend/data/documents/compliance/eu_amlr_1624.html"

    from pathlib import Path as _P
    doc_path = pdf_path if _P(pdf_path).exists() else (
        html_path if _P(html_path).exists() else None
    )
    if not doc_path:
        print("❌ No EU AMLR document found. Place PDF at:", pdf_path)
        return

    result = builder.index_document(doc_path, source_name="EU_AMLR_1624", drop_existing=True)
    print(f"\n✅ Indexing complete: {result}")
    print(f"\n📊 Stats: {builder.get_stats()}")

    # Quick smoke-test
    print("\n🔍 Smoke-test search: 'customer due diligence'")
    for r in builder.search("customer due diligence", limit=3):
        print(f"  [{r['section']}] relevance={r['relevance']}  {r['content'][:120]}…")


if __name__ == "__main__":
    main()
