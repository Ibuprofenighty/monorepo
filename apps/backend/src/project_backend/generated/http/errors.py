"""AUTO-GENERATED from contracts/errors/*.yaml — do not edit."""

from __future__ import annotations


class ErrorCode:
    """Stable public error codes. Use these, never string literals."""

    CATALOG_RESOURCE_LOCKED = "CATALOG.RESOURCE_LOCKED"
    AUTHN_REQUIRED = "AUTHN.REQUIRED"
    AUTHN_INVALID = "AUTHN.INVALID"
    AUTHZ_DENIED = "AUTHZ.DENIED"
    NOT_FOUND = "NOT.FOUND"
    VALIDATION_FAILED = "VALIDATION.FAILED"
    RATE_LIMITED = "RATE.LIMITED"
    INTERNAL = "INTERNAL"


ERROR_HTTP_STATUS: dict[str, int] = {
    ErrorCode.CATALOG_RESOURCE_LOCKED: 409,
    ErrorCode.AUTHN_REQUIRED: 401,
    ErrorCode.AUTHN_INVALID: 401,
    ErrorCode.AUTHZ_DENIED: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.VALIDATION_FAILED: 422,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL: 500,
}


ERROR_TYPES: dict[str, str] = {
    ErrorCode.CATALOG_RESOURCE_LOCKED: "https://api.example.com/problems/catalog/resource-locked",
    ErrorCode.AUTHN_REQUIRED: "https://api.example.com/problems/authn/required",
    ErrorCode.AUTHN_INVALID: "https://api.example.com/problems/authn/invalid",
    ErrorCode.AUTHZ_DENIED: "https://api.example.com/problems/authz/denied",
    ErrorCode.NOT_FOUND: "https://api.example.com/problems/not-found",
    ErrorCode.VALIDATION_FAILED: "https://api.example.com/problems/validation-failed",
    ErrorCode.RATE_LIMITED: "https://api.example.com/problems/rate-limited",
    ErrorCode.INTERNAL: "https://api.example.com/problems/internal",
}


ERROR_TITLES: dict[str, str] = {
    ErrorCode.CATALOG_RESOURCE_LOCKED: "Resource is locked",
    ErrorCode.AUTHN_REQUIRED: "Authentication required",
    ErrorCode.AUTHN_INVALID: "Invalid credentials",
    ErrorCode.AUTHZ_DENIED: "Operation not allowed",
    ErrorCode.NOT_FOUND: "Resource not found",
    ErrorCode.VALIDATION_FAILED: "Request validation failed",
    ErrorCode.RATE_LIMITED: "Too many requests",
    ErrorCode.INTERNAL: "Internal error",
}
