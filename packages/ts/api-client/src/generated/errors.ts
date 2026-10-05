// AUTO-GENERATED from contracts/errors/*.yaml — do not edit.
// Regenerate: make generate

export const ErrorCodes = {
  "CATALOG.RESOURCE_LOCKED": 409,
  "AUTHN.REQUIRED": 401,
  "AUTHN.INVALID": 401,
  "AUTHZ.DENIED": 403,
  "NOT.FOUND": 404,
  "VALIDATION.FAILED": 422,
  "RATE.LIMITED": 429,
  "INTERNAL": 500,
} as const;

export type ErrorCode = keyof typeof ErrorCodes;

export const ErrorTypes: Record<ErrorCode, string> = {
  "CATALOG.RESOURCE_LOCKED": "https://api.example.com/problems/catalog/resource-locked",
  "AUTHN.REQUIRED": "https://api.example.com/problems/authn/required",
  "AUTHN.INVALID": "https://api.example.com/problems/authn/invalid",
  "AUTHZ.DENIED": "https://api.example.com/problems/authz/denied",
  "NOT.FOUND": "https://api.example.com/problems/not-found",
  "VALIDATION.FAILED": "https://api.example.com/problems/validation-failed",
  "RATE.LIMITED": "https://api.example.com/problems/rate-limited",
  "INTERNAL": "https://api.example.com/problems/internal",
};
