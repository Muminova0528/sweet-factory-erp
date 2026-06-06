# Stage 1: Backend build
FROM python:3.12-slim AS backend

WORKDIR /backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# Stage 2: Frontend build (agar frontend build qilinadigan bo'lsa)
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
# Agar frontend da package.json bo'lsa (React/Vue)
# COPY frontend/package*.json ./
# RUN npm install
# COPY frontend/ .
# RUN npm run build
# Agar faqat static HTML bo'lsa, bu stage kerak emas

# Stage 3: Final image
FROM python:3.12-slim

# Kerakli paketlarni o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/nginx

# Backend kodini copy qilish
WORKDIR /app
COPY --from=backend /backend /app/backend
COPY --from=backend /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Frontend fayllarni copy qilish (agar static HTML bo'lsa)
COPY frontend/ /usr/share/nginx/html/

# Nginx konfiguratsiyasini copy qilish
RUN rm -f /etc/nginx/nginx.conf
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Environment variables
ENV PYTHONPATH=/app
ENV APP_ENV=production

WORKDIR /app/backend

# Portlarni ochish
EXPOSE 80
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Backend va Nginx ni birga ishga tushirish
CMD service nginx start && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2