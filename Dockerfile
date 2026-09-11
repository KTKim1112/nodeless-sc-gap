# Production image: one container, one port, both halves of the application.
#
# Multi-stage, because building the frontend needs Node and running the
# application does not. Only the built static files cross the boundary, so
# node_modules -- a few hundred megabytes of build tooling -- never reaches the
# image that ships.

# --- stage 1: build the frontend ---------------------------------------------

FROM node:24-alpine AS frontend

WORKDIR /build

# Dependencies first and separately from the source: this layer is cached and
# only rebuilds when package-lock.json changes, which is far less often than
# the source does.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# vite.config.ts writes to ../backend/static, which does not exist in this
# stage. Overridden here so the output lands somewhere this stage owns.
RUN npx vite build --outDir dist --emptyOutDir


# --- stage 2: the application ------------------------------------------------

FROM python:3.12-slim AS runtime

# PYTHONDONTWRITEBYTECODE: the filesystem is read-mostly, so .pyc files are
# just noise. PYTHONUNBUFFERED: otherwise logs appear only when a buffer fills,
# which makes `docker logs` useless for watching a run.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Same caching argument as above, and pyproject.toml stays the single place the
# dependencies are declared -- repeating them here would be one more list to
# forget. The stub package is what lets setuptools resolve the project before
# the real source is copied, so the dependency layer is cached independently of
# the code.
COPY backend/pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py && pip install --no-cache-dir .

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

# A non-root user, because nothing here needs to write anywhere. The code and
# the built page are read-only as far as the application is concerned.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

# The health check is the reason /api/health exists: it lets an orchestrator
# tell "the process is up" from "the application is answering".
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# One worker: the analysis is CPU-bound NumPy and the Monte Carlo already runs
# in a thread, and the job store is in process memory, so a second worker would
# not share it (plan.md section 5).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
