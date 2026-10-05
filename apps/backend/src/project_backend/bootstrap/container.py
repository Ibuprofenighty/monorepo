"""Composition root. Builds the Container; knows concrete implementations.

Nothing else in the codebase may import from bootstrap (blueprint 04 §3).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from project_backend.kernel.authorization import Authorizer
from project_backend.modules.catalog.wiring import build_authorizer
from project_backend.platform.authn.active import Verifier, build_verifier
from project_backend.platform.config.settings import Settings
from project_backend.platform.db.session import create_engine_and_sessionmaker


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker
    verifier: Verifier
    authorizer: Authorizer


def build_container(settings: Settings) -> Container:
    engine, session_factory = create_engine_and_sessionmaker(settings.database_url)
    verifier = build_verifier(settings)
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        verifier=verifier,
        authorizer=build_authorizer(),
    )
