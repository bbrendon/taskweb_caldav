# Stage 1: build Vue SPA
FROM node:20-slim AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + built SPA
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=frontend /app/dist ./spa
RUN mkdir -p staticfiles

EXPOSE 38000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:38000", "--workers", "2", "--timeout", "30"]
