# --- frontend build ---
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/ ./
# vite.config.ts outputs to ../backend/app/static for local dev; build into ./dist here.
RUN npm ci && npx vue-tsc --noEmit && npx vite build --outDir dist --emptyOutDir

# --- app ---
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY task-caldav-lib/ /tmp/task-caldav-lib/
COPY backend/pyproject.toml backend/
COPY backend/app backend/app
RUN pip install /tmp/task-caldav-lib ./backend && rm -rf /tmp/task-caldav-lib
COPY config/ config/
COPY --from=web /web/dist/ backend/app/static/
WORKDIR /app/backend
EXPOSE 38000
# Exactly one worker: the task index lives in process memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "38000", "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
