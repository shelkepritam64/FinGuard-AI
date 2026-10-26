# FinGuard AI — Production Backend Dockerfile
# Optimized for AWS App Runner, ECS Fargate, or Docker Compose
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system utilities needed for health checks and security
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app
COPY scripts/ ./scripts
COPY pyproject.toml .

# Create runtime directory for reports and local fallback
RUN mkdir -p /app/data/reports && \
    chmod -R 755 /app/data

# Security: Create non-root user and drop root privileges
RUN useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# AWS container health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production command with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
