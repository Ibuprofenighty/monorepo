"""Selected identity adapter. The generator rewrites the import below."""

from project_backend.platform.authn.verifiers.local import (
    Verifier,
    build_verifier,
    mint_token,
    register_auth_routes,
    verify_bearer_token,
)

__all__ = [
    "Verifier",
    "build_verifier",
    "mint_token",
    "register_auth_routes",
    "verify_bearer_token",
]
