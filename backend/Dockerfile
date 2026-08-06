# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed to compile some Python packages (e.g. PyMuPDF, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy entire repo (backend + any shared modules it imports)
COPY . .

# Create persistent data directories (Railway mounts a volume here)
RUN mkdir -p backend/data backend/reports backend/data/resumes

# Expose default port (Railway overrides via $PORT env var)
EXPOSE 8000

# Start FastAPI via uvicorn — PORT is injected by Railway at runtime
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
