import math

from google.genai import types

from app.config import get_settings
from app.services.llm import get_client

settings = get_settings()


def _normalize(vector: list[float]) -> list[float]:
    """Renormalizes to unit length after MRL dimensionality truncation, per Google's guidance."""
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    if not texts:
        return []
    response = get_client().models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=settings.embedding_dimensions,
        ),
    )
    return [_normalize(embedding.values) for embedding in response.embeddings]


def embed_document_chunks(texts: list[str]) -> list[list[float]]:
    return _embed(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    return _embed([text], task_type="RETRIEVAL_QUERY")[0]
