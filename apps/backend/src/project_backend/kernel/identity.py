"""Trusted principal representation. Decoupled from HTTP, JWT, Keycloak, WeChat.

A Principal is created ONLY by the selected platform/authn verifier after
credential verification. Never trust client-supplied identity fields (blueprint 08 §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str] = field(default_factory=frozenset)
    # Project-specific claims (tenant_id, etc.) go here as explicit fields —
    # never as an untyped dict.
