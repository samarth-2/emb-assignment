# Build context is the repo root (see docker-compose.yml / `docker build -f backend/Dockerfile .`)
# so this stage can COPY both backend/ and the sibling dataset/ folder the seed script needs.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

COPY backend/ .
COPY dataset/ /dataset/

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
