"""FastAPI dependencies shared by all modules' presentation layers."""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from project_backend.kernel.identity import Principal
from project_backend.platform.authn.active import verify_bearer_token

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request):
    return request.app.state.container


async def get_session(request: Request) -> AsyncSession:  # type: ignore[misc]
    container = get_container(request)
    async with container.session_factory() as session:
        yield session


async def get_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    container = get_container(request)
    return verify_bearer_token(container.verifier, creds.credentials if creds else None)


def get_authorizer(request: Request):
    return get_container(request).authorizer
