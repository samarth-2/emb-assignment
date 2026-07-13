import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.document import DocumentChunk
from app.services.retrieval import search_documents


def _seeded_session_or_skip():
    try:
        db = SessionLocal()
        has_chunks = db.scalar(select(DocumentChunk.id).limit(1)) is not None
    except Exception as exc:  # noqa: BLE001 - any connectivity failure means "skip"
        pytest.skip(f"Postgres/pgvector not reachable: {exc}")
    if not has_chunks:
        db.close()
        pytest.skip("document_chunks is empty; run `python -m scripts.seed` first")
    return db


def test_relevant_query_returns_matching_chunk():
    db = _seeded_session_or_skip()
    try:
        result = search_documents(db, "What is the refund window?")
        assert result.has_results
        assert any(
            c.document == "Northwind Gadgets — Returns and Refunds Policy" for c in result.citations
        )
    finally:
        db.close()


def test_offtopic_query_returns_no_results():
    db = _seeded_session_or_skip()
    try:
        result = search_documents(db, "Who won the 2011 cricket world cup?")
        assert not result.has_results
    finally:
        db.close()
