"""Composition helpers for bootstrap. Wiring knows concrete implementations;
application code only knows ports."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from project_backend.modules.catalog.application.access import LocalAuthorizer
from project_backend.modules.catalog.infrastructure.persistence.repository import (
    SqlAlchemyUnitOfWork,
)


def get_uow(session: AsyncSession) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def build_authorizer() -> LocalAuthorizer:
    return LocalAuthorizer()
