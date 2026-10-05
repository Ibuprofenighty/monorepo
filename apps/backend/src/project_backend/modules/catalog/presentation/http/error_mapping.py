"""Module errors → public codes. This is the ONLY place that decides the mapping
(domain → presentation). The generic platform handler only serializes (blueprint 03 §6)."""

from __future__ import annotations

from project_backend.generated.http.errors import ErrorCode
from project_backend.kernel.errors import AuthenticationError, AuthorizationError
from project_backend.modules.catalog.application.commands.create_resource import IdempotencyConflict
from project_backend.modules.catalog.domain.errors import (
    DomainError,
    DuplicateResource,
    ResourceLocked,
    ResourceNotFound,
)
from project_backend.platform.http.exception_handlers import MappedError


def to_mapped_error(exc: Exception) -> MappedError:
    if isinstance(exc, ResourceNotFound):
        return MappedError(ErrorCode.NOT_FOUND, f"resource not found: {exc.resource_id}")
    if isinstance(exc, ResourceLocked):
        return MappedError(
            ErrorCode.CATALOG_RESOURCE_LOCKED, f"resource is locked: {exc.resource_id}"
        )
    if isinstance(exc, (DuplicateResource, IdempotencyConflict)):
        return MappedError(ErrorCode.VALIDATION_FAILED, str(exc))
    if isinstance(exc, AuthorizationError):
        return MappedError(ErrorCode.AUTHZ_DENIED)
    if isinstance(exc, AuthenticationError):
        return MappedError(ErrorCode.AUTHN_INVALID)
    if isinstance(exc, DomainError):
        return MappedError(ErrorCode.VALIDATION_FAILED, str(exc))
    raise exc
