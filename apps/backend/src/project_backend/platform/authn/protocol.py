"""Identity adapter contract.

Each module under verifiers/ exports Verifier, verify_bearer_token, mint_token,
build_verifier, and register_auth_routes. active.py is the only import site.
A new identity is a new module plus the generator rewriting that import.

Cloud verifiers (aws, gcp, azure, alibaba, and others) are not implemented.
"""

from __future__ import annotations

REQUIRED_EXPORTS = (
    "Verifier",
    "build_verifier",
    "mint_token",
    "register_auth_routes",
    "verify_bearer_token",
)


class UnsupportedMint(Exception):
    """The selected identity does not issue bearer tokens."""
