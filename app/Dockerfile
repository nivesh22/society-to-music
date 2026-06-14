# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Runtime (FastAPI + static frontend) ──────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY production/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY production/ ./production/

# Copy built React app — served as static files by FastAPI
COPY --from=frontend /frontend/dist/ ./static/

# GCP Secret Manager is used when USE_SECRET_MANAGER=true (set by Cloud Run)
ENV USE_SECRET_MANAGER=false
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "production.api:app", "--host", "0.0.0.0", "--port", "8080"]
