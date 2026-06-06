# ─────────────────────────────────────────────────────────────────────────────
# Sweet Factory ERP — Backend Dockerfile
# Multi-stage build for minimal production image
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies needed for compilation
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Production image
FROM python:3.12-slim AS production

LABEL maintainer="Sweet Factory DevOps <devops@sweetfactory.com>"
LABEL version="1.0.0"
LABEL description="Sweet Factory Cloud ERP Backend"

# Install only runtime system libraries
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r sweetfactory && \
    useradd -r -g sweetfactory -d /app -s /sbin/nologin sweetfactory

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY --chown=sweetfactory:sweetfactory . .

# Switch to non-root user
USER sweetfactory

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose application port
EXPOSE 8000

# Start with Uvicorn — production-ready ASGI server
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--access-log", \
     "--log-level", "info"]
