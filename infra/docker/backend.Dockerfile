# Backend image: uv workspace, multi-stage (blueprint 09 §3).
# Build from repo root: docker build -f infra/docker/backend.Dockerfile .
# Base images are digest-pinned (Batch D). Update digests via Dependabot;
# the toolchain gate (check_toolchain.py) verifies version consistency.
ARG PYTHON_VERSION=3.12
ARG UV_DIGEST=sha256:5d275ca5f0da33c3368ac8fbb85fafabad023b3b8a7cff39a94ac0baecfd9a50
ARG PYTHON_DIGEST=sha256:9901e0a8d75037d8242ed43155cbcb2d1f61be1356383d8054afb59fd50e39c4

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim@${UV_DIGEST} AS builder
# Same path as the runtime stage: venv entry-point shebangs are absolute.
WORKDIR /srv/app
# Workspace metadata first for layer caching. Workspace members are not
# installed; the runtime puts the backend source on PYTHONPATH.
COPY pyproject.toml uv.lock .python-version ./
COPY apps/backend/pyproject.toml apps/backend/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package project-backend --no-install-workspace

FROM python:${PYTHON_VERSION}-slim-bookworm@${PYTHON_DIGEST} AS runtime
WORKDIR /srv/app
RUN useradd -r -u 10001 app && mkdir -p /srv/app && chown app:app /srv/app
# Copy the synced environment and the backend source.
COPY --from=builder /srv/app/.venv /srv/app/.venv
COPY apps/backend/src /srv/app/src
COPY apps/backend/alembic.ini /srv/app/
COPY apps/backend/migrations /srv/app/migrations
COPY contracts /srv/app/contracts
ENV PATH="/srv/app/.venv/bin:$PATH" \
    PYTHONPATH="/srv/app/src" \
    PYTHONDONTWRITEBYTECODE=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
CMD ["uvicorn", "project_backend.entrypoints.http:app", "--host", "0.0.0.0", "--port", "8000"]
