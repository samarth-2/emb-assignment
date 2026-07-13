from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document, DocumentChunk
from app.services.embeddings import embed_query

settings = get_settings()


@dataclass
class Citation:
    document: str
    section: str | None
    snippet: str


@dataclass
class RetrievalResult:
    chunks: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)

    @property
    def has_results(self) -> bool:
        return bool(self.chunks)


def search_documents(db: Session, query: str) -> RetrievalResult:
    """Tool entrypoint: embeds the query and returns the nearest chunks (with citations).

    Chunks farther than `retrieval_distance_threshold` (cosine distance) are dropped, so an
    off-topic query yields an empty result rather than a weak, irrelevant match.
    """
    query_embedding = embed_query(query)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    rows = db.execute(
        select(Document.title, DocumentChunk.section, DocumentChunk.content, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .order_by(distance)
        .limit(settings.retrieval_top_k)
    ).all()

    relevant = [row for row in rows if row.distance <= settings.retrieval_distance_threshold]
    return RetrievalResult(
        chunks=[row.content for row in relevant],
        citations=[
            Citation(document=row.title, section=row.section, snippet=row.content[:200])
            for row in relevant
        ],
    )
