"""Minimal shared exception protocol (blueprint 03 §1).

Business errors live in their module's domain/errors.py.
Public codes live in generated/http/errors.py. This file stays tiny.
"""

from __future__ import annotations


class AuthenticationError(Exception):
    """Credential missing/invalid. Maps to AUTHN.* (never leaks which part failed)."""


class AuthorizationError(Exception):
    """Authoritative DENY. Maps to AUTHZ.DENIED. Must cause zero business side effects."""
