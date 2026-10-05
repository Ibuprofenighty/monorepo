"""Application factory.

Contract-first: the served OpenAPI IS the hand-written contracts/http/openapi.yaml
(blueprint 02 §1). FastAPI's auto-generated schema is replaced. tests/contract/
proves the implementation matches it on every run.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from project_backend.bootstrap.container import Container, build_container
from project_backend.modules.catalog.presentation.http.router import router as catalog_router
from project_backend.platform.authn.active import register_auth_routes
from project_backend.platform.capabilities import dependency_checks
from project_backend.platform.config.settings import Settings
from project_backend.platform.http import deps  # noqa: F401  (dependency callables)
from project_backend.platform.http.exception_handlers import register_exception_handlers
from project_backend.platform.http.middleware import TraceIdMiddleware
from project_backend.platform.observability.logging import install_trace_filter, setup_logging


def load_contract_openapi(settings: Settings) -> dict:
    # Resolved relative to the REPO root (contracts/ is a repo-level dir).
    candidates = [
        Path(settings.openapi_source_path),
        Path(__file__).resolve().parents[5] / settings.openapi_source_path,
    ]
    for p in candidates:
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"openapi root must be a mapping: {p}"
            return data
    raise FileNotFoundError(f"contract source not found: {settings.openapi_source_path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    install_trace_filter()
    yield
    container: Container = app.state.container
    await container.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    container = build_container(settings)

    # API docs are a development aid, not a production surface (P1).
    docs_enabled = not settings.is_deployed
    app = FastAPI(
        title=f"{settings.project_name} API",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
    )
    app.state.container = container

    app.add_middleware(TraceIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    # Module routers — one include per module, always under the versioned prefix.
    app.include_router(catalog_router, prefix=settings.api_v1_prefix)
    app.include_router(_health_router(settings), prefix=settings.api_v1_prefix)
    register_auth_routes(app, settings)

    # Contract-first: serve the hand-written source, not FastAPI's inference.
    contract = load_contract_openapi(settings)

    def custom_openapi() -> dict:  # type: ignore[no-redef]
        return contract

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


def _health_router(settings: Settings) -> APIRouter:
    """Liveness + readiness probes. Platform concern, not a business module."""
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": settings.version}

    @router.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        """Readiness: selected dependencies must answer. Returns 503 otherwise."""
        container: Container = request.app.state.container
        checks = await dependency_checks(settings, container.engine)
        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        )

    return router
