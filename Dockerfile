# =============================================================
# Coal Dashboard — Single-container build for Railway
# Stage 1: Build React frontend
# Stage 2: Python backend serving built static files
# =============================================================

# ---- Stage 1: Build the React frontend ----
FROM node:22-alpine AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python backend + built frontend ----
FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for C extensions (lxml, numpy, pandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy built frontend from stage 1 into /app/static
COPY --from=frontend-build /build/dist /app/static

# Create data directory for SQLite (Railway volume mount point)
RUN mkdir -p /data

# Railway injects PORT env var; default to 8000
ENV PORT=8000
ENV STATIC_DIR=/app/static
ENV DATABASE_PATH=/data/coal_dashboard.db
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

# Use shell form so $PORT is expanded at runtime
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
