# ========================================================
# Stage 1: Build Frontend (React + Vite)
# ========================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies first for better layer caching
COPY frontend/package*.json ./
RUN npm ci || npm install

# Copy source code and build production bundle
COPY frontend/ ./
RUN npm run build

# ========================================================
# Stage 2: Runtime Environment (FastAPI + Python)
# ========================================================
FROM python:3.11-slim

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENVIRONMENT=production

WORKDIR /app

# Install system dependencies required for compilation and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/app ./app
COPY backend/scripts ./scripts

# Copy built frontend assets from Stage 1 into the backend static folder
COPY --from=frontend-builder /app/frontend/dist ./app/static

# Expose application port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
