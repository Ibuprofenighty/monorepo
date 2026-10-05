"""Authorization interface + decision types. No policy storage here (blueprint 08 §2).

Exactly ONE authority decides per deployment: local (modules/<m>/application/access.py)
or remote (platform/authz/client.py). Never both in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from project_backend.kernel.identity import Principal


class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    # No ABSTAIN: the authority must decide. Unknown → DENY (fail-closed).


@dataclass(frozen=True)
class Action:
    """What is being attempted, e.g. Action("resource.delete")."""

    name: str


@dataclass(frozen=True)
class ResourceRef:
    """Trusted facts about the target, built from backend state (never client input)."""

    kind: str
    id: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)


class Authorizer(Protocol):
    def decide(self, principal: Principal, action: Action, resource: ResourceRef) -> Decision: ...
