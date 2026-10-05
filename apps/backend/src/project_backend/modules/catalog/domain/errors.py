"""Domain errors. Pure business facts — no HTTP, no public codes here (blueprint 03 §1)."""

from __future__ import annotations


class DomainError(Exception):
    """Base for catalog domain errors."""


class ResourceNotFound(DomainError):
    def __init__(self, resource_id: str) -> None:
        super().__init__(f"resource not found: {resource_id}")
        self.resource_id = resource_id


class ResourceLocked(DomainError):
    def __init__(self, resource_id: str) -> None:
        super().__init__(f"resource is locked: {resource_id}")
        self.resource_id = resource_id


class DuplicateResource(DomainError):
    def __init__(self, name: str) -> None:
        super().__init__(f"duplicate resource name: {name}")
        self.name = name
