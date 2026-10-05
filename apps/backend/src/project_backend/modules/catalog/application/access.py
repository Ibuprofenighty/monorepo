"""Local authorization policy — the single authority for this deployment (blueprint 08 §2).

Facts come from trusted backend state (the loaded Resource), never from client
input. DENY → AuthorizationError → AUTHZ.DENIED with zero side effects.
"""

from __future__ import annotations

from project_backend.kernel.authorization import Action, Authorizer, Decision, ResourceRef
from project_backend.kernel.errors import AuthorizationError
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.domain.resource import Resource


class LocalAuthorizer:
    """Default local authority. Policy: reads need any authenticated principal;
    writes need the 'editor' role. Promote to modules/access/ when shared."""

    def decide(self, principal: Principal, action: Action, resource: ResourceRef) -> Decision:
        if action.name in ("resource.read", "resource.list"):
            return Decision.ALLOW
        if action.name in ("resource.create", "resource.delete"):
            return Decision.ALLOW if "editor" in principal.roles else Decision.DENY
        return Decision.DENY  # fail-closed on unknown actions


def ensure_can(
    authorizer: Authorizer, principal: Principal, action_name: str, resource: Resource
) -> None:
    ref = ResourceRef(
        kind="resource",
        id=resource.id,
        attributes={"locked": str(resource.locked)},
    )
    if authorizer.decide(principal, Action(action_name), ref) is not Decision.ALLOW:
        raise AuthorizationError(f"denied: {action_name} on resource {resource.id}")
