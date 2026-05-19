"""
Document parser for compliance documents (HTML, PDF, TXT)

Phase 5 upgrade:
- Article and Recital boundary detection
- Rich metadata per chunk (article_num, recital_num, chapter, type)
- Smaller, more targeted chunks (200-600 chars) for precise retrieval
- Clean section labels: "Article 13", "Recital 40", "Chapter II", etc.
"""

from bs4 import BeautifulSoup
from typing import List, Optional
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DocumentChunk:
    """Represents a chunk of document content with rich legal metadata"""
    content: str
    section: str                         # e.g. "Article 13", "Recital 40", "Chapter II"
    subsection: Optional[str]            # e.g. paragraph label or sub-article
    page_num: Optional[int]
    chunk_id: str
    source: str
    # --- new rich metadata fields ---
    article_num: Optional[int] = None    # 13
    recital_num: Optional[int] = None    # 40
    chapter: Optional[str] = None        # "Chapter II"
    legal_type: str = "general"          # "article" | "recital" | "chapter" | "general"


# ─── regex patterns for legal structure ───────────────────────────────────────
_RE_ARTICLE  = re.compile(r'^article\s+(\d+)\b', re.IGNORECASE)
_RE_RECITAL  = re.compile(r'^\((\d+)\)\s')           # "(40) Obliged entities..."
_RE_CHAPTER  = re.compile(r'^chapter\s+(i{1,3}v?|vi{0,3}|ix|x{0,3})\b', re.IGNORECASE)
_RE_TITLE    = re.compile(r'^title\s+(i{1,3}v?|vi{0,3}|ix|x{0,3})\b', re.IGNORECASE)
_RE_SECTION  = re.compile(r'^section\s+\d+', re.IGNORECASE)
# inline article reference inside a paragraph (for section detection from PDF)
_RE_INLINE_ARTICLE = re.compile(r'article\s+(\d+)', re.IGNORECASE)
_RE_INLINE_RECITAL = re.compile(r'recital\s+(\d+)', re.IGNORECASE)


def _detect_legal_header(line: str):
    """Detect if a line is a legal structure header.

    Returns (legal_type, label, num) or None.
    """
    stripped = line.strip()
    if not stripped:
        return None

    m = _RE_ARTICLE.match(stripped)
    if m:
        return ("article", f"Article {m.group(1)}", int(m.group(1)))

    m = _RE_RECITAL.match(stripped)
    if m:
        return ("recital", f"Recital {m.group(1)}", int(m.group(1)))

    m = _RE_CHAPTER.match(stripped)
    if m:
        return ("chapter", f"Chapter {m.group(1).upper()}", None)

    m = _RE_TITLE.match(stripped)
    if m:
        return ("title", f"Title {m.group(1).upper()}", None)

    m = _RE_SECTION.match(stripped)
    if m:
        return ("section", stripped[:60], None)

    return None


def _infer_section_from_content(text: str):
    """Infer article/recital number from the content of a paragraph."""
    # Recital style: paragraph starting with "(40)"
    m = _RE_RECITAL.match(text.strip())
    if m:
        n = int(m.group(1))
        return f"Recital {n}", "recital", n, None

    # Inline "Article 13" reference in first 200 chars
    m = _RE_INLINE_ARTICLE.search(text[:200])
    if m:
        n = int(m.group(1))
        return f"Article {n}", "article", None, n

    return None, "general", None, None


class DocumentParser:
    """Parse compliance documents and create structured chunks with legal metadata."""

    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 600):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    # ──────────────────────────────────────────────────────────────────────────
    # PDF parsing
    # ──────────────────────────────────────────────────────────────────────────

    def parse_pdf(self, pdf_path: str, source_name: str = "unknown") -> List[DocumentChunk]:
        """Parse PDF and create chunks with article/recital metadata."""
        try:
            import PyPDF2
        except ImportError:
            raise ImportError("PyPDF2 required. Install with: pip install PyPDF2")

        chunks: List[DocumentChunk] = []
        chunk_idx = 0
        current_lines: List[str] = []
        current_section = "General"
        current_chapter = None
        current_article_num = None
        current_recital_num = None
        current_legal_type = "general"

        def flush(page_num):
            nonlocal chunk_idx
            if not current_lines:
                return
            text = " ".join(current_lines).strip()
            text = self.clean_text(text)
            if len(text) < self.min_chunk_size:
                return
            chunks.append(DocumentChunk(
                content=text[:5000],
                section=current_section,
                subsection=None,
                page_num=page_num,
                chunk_id=f"{source_name}_chunk_{chunk_idx}",
                source=source_name,
                article_num=current_article_num,
                recital_num=current_recital_num,
                chapter=current_chapter,
                legal_type=current_legal_type,
            ))
            chunk_idx += 1

        with open(pdf_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            total = len(reader.pages)
            print(f"  • Processing {total} pages…")

            for page_idx, page in enumerate(reader.pages):
                raw = page.extract_text() or ""
                raw = self.clean_text(raw)

                for line in raw.split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    header = _detect_legal_header(line)
                    if header:
                        # Flush current accumulator
                        flush(page_idx + 1)
                        current_lines = []

                        h_type, h_label, h_num = header
                        current_section = h_label
                        current_legal_type = h_type

                        if h_type == "article":
                            current_article_num = h_num
                            current_recital_num = None
                        elif h_type == "recital":
                            current_recital_num = h_num
                            current_article_num = None
                        elif h_type in ("chapter", "title", "section"):
                            current_chapter = h_label
                            current_article_num = None
                            current_recital_num = None

                        # Include the header line itself in the accumulator
                        current_lines.append(line)
                    else:
                        current_lines.append(line)

                    # Flush when chunk is large enough
                    joined = " ".join(current_lines)
                    if len(joined) >= self.max_chunk_size:
                        flush(page_idx + 1)
                        current_lines = []

                if (page_idx + 1) % 20 == 0:
                    print(f"    … {page_idx + 1}/{total} pages")

        # Flush remainder
        flush(total)
        return chunks

    # ──────────────────────────────────────────────────────────────────────────
    # HTML parsing
    # ──────────────────────────────────────────────────────────────────────────

    def parse_html(self, html_content: str, source_name: str = "unknown") -> List[DocumentChunk]:
        """Parse HTML document and create chunks with article/recital metadata."""
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        chunks: List[DocumentChunk] = []
        chunk_idx = 0
        current_lines: List[str] = []
        current_section = "General"
        current_chapter = None
        current_article_num = None
        current_recital_num = None
        current_legal_type = "general"

        def flush():
            nonlocal chunk_idx
            if not current_lines:
                return
            text = " ".join(current_lines).strip()
            text = self.clean_text(text)
            if len(text) < self.min_chunk_size:
                return
            chunks.append(DocumentChunk(
                content=text[:5000],
                section=current_section,
                subsection=None,
                page_num=None,
                chunk_id=f"{source_name}_chunk_{chunk_idx}",
                source=source_name,
                article_num=current_article_num,
                recital_num=current_recital_num,
                chapter=current_chapter,
                legal_type=current_legal_type,
            ))
            chunk_idx += 1

        for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            text = el.get_text(separator=" ", strip=True)
            if not text:
                continue

            # Heading tags always start a new section
            if el.name in ("h1", "h2", "h3", "h4"):
                flush()
                current_lines = []
                header = _detect_legal_header(text)
                if header:
                    h_type, h_label, h_num = header
                    current_section = h_label
                    current_legal_type = h_type
                    if h_type == "article":
                        current_article_num = h_num
                        current_recital_num = None
                    elif h_type == "recital":
                        current_recital_num = h_num
                        current_article_num = None
                    elif h_type in ("chapter", "title", "section"):
                        current_chapter = h_label
                else:
                    current_section = text[:80]
                continue

            # Paragraph / list item: detect recital pattern inline
            current_lines.append(text)
            joined = " ".join(current_lines)
            if len(joined) >= self.max_chunk_size:
                flush()
                current_lines = []

        flush()
        return chunks

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def clean_text(self, text: str) -> str:
        """Normalize whitespace and strip control characters."""
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def parse_document(self, file_path: str, source_name: str = "unknown") -> List[DocumentChunk]:
        """Auto-detect format from extension and parse."""
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self.parse_pdf(file_path, source_name)
        elif ext in (".html", ".htm"):
            with open(file_path, "r", encoding="utf-8") as fh:
                return self.parse_html(fh.read(), source_name)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def save_chunks_metadata(chunks: List[DocumentChunk], output_path: str) -> None:
        """Save chunk metadata to JSON for inspection."""
        import json
        data = [
            {
                "chunk_id": c.chunk_id,
                "section": c.section,
                "subsection": c.subsection,
                "article_num": c.article_num,
                "recital_num": c.recital_num,
                "chapter": c.chapter,
                "legal_type": c.legal_type,
                "source": c.source,
                "content_length": len(c.content),
            }
            for c in chunks
        ]
        with open(output_path, "w") as fh:
            json.dump(data, fh, indent=2)
        print(f"  ✓ Saved metadata for {len(data)} chunks → {output_path}")
