from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_HEADING_MAX_WORDS = 6
_TERMINAL_PUNCTUATION = ".,;:!?"


@dataclass
class Chunk:
    section: str | None
    content: str


def _is_heading_line(line: str) -> bool:
    if not line or line[-1] in _TERMINAL_PUNCTUATION:
        return False
    return len(line.split()) <= _HEADING_MAX_WORDS


def extract_title_and_chunks(pdf_path: Path) -> tuple[str, list[Chunk]]:
    """Splits a policy PDF into (title, section chunks).

    Assumes the first extracted line is the document title, and that each later
    short line with no terminal punctuation is a section heading whose paragraph
    runs until the next heading. Validated against this project's 5 policy PDFs,
    which are single-page and consistently structured this way.
    """
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        raise ValueError(f"No extractable text in {pdf_path}")

    title = lines[0]
    chunks: list[Chunk] = []
    heading: str | None = None
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            chunks.append(Chunk(section=heading, content=" ".join(paragraph)))

    for line in lines[1:]:
        if _is_heading_line(line):
            flush()
            heading = line
            paragraph = []
        else:
            paragraph.append(line)
    flush()

    return title, chunks


def chunk_text_for_embedding(title: str, chunk: Chunk) -> str:
    """Prefixes the document title and section heading so the embedding captures context."""
    heading_part = f"{chunk.section}\n" if chunk.section else ""
    return f"{title}\n{heading_part}{chunk.content}"
