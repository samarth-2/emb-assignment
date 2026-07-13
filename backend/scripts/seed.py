"""Idempotent seed script. Run: python -m scripts.seed"""

import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk
from app.models.order import Order
from app.models.user import User
from app.services.embeddings import embed_document_chunks
from app.services.ingestion import chunk_text_for_embedding, extract_title_and_chunks

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
ORDERS_CSV = DATASET_DIR / "orders.csv"


def seed_admin_user() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.username == DEFAULT_ADMIN_USERNAME))
        if existing is not None:
            print(f"Admin user '{DEFAULT_ADMIN_USERNAME}' already exists, skipping.")
            return
        db.add(
            User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            )
        )
        db.commit()
        print(f"Created admin user '{DEFAULT_ADMIN_USERNAME}'.")
    finally:
        db.close()


def seed_orders() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Order.order_id).limit(1)) is not None:
            print("Orders already seeded, skipping.")
            return

        with ORDERS_CSV.open(newline="") as f:
            rows = list(csv.DictReader(f))

        orders = [
            Order(
                order_id=row["order_id"],
                customer=row["customer"],
                product=row["product"],
                amount=int(row["amount"]),
                status=row["status"],
                order_date=date.fromisoformat(row["order_date"]),
            )
            for row in rows
        ]
        db.add_all(orders)
        db.commit()
        print(f"Seeded {len(orders)} orders.")
    finally:
        db.close()


def seed_documents() -> None:
    db = SessionLocal()
    try:
        for pdf_path in sorted(DATASET_DIR.glob("*.pdf")):
            if db.scalar(select(Document).where(Document.filename == pdf_path.name)) is not None:
                print(f"Document '{pdf_path.name}' already ingested, skipping.")
                continue

            title, chunks = extract_title_and_chunks(pdf_path)
            texts = [chunk_text_for_embedding(title, chunk) for chunk in chunks]
            embeddings = embed_document_chunks(texts)

            document = Document(filename=pdf_path.name, title=title)
            db.add(document)
            db.flush()

            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk.content,
                        section=chunk.section,
                        embedding=embedding,
                    )
                )
            db.commit()
            print(f"Ingested '{pdf_path.name}' ({title}): {len(chunks)} chunks.")
    finally:
        db.close()


def main() -> None:
    seed_admin_user()
    seed_orders()
    seed_documents()


if __name__ == "__main__":
    main()
