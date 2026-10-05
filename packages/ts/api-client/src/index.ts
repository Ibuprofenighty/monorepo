/**
 * Public entry. Small on purpose (blueprint 02 §5): transport adapters live
 * in each app, not here.
 */
export { ApiClient, type ClientOptions } from "./client";
export type { Health, Resource, ResourceCreate, ResourceList } from "./client";
export type { ApiRequest, ApiResponse, Transport } from "./runtime/transport";
export type { Problem } from "./runtime/problem";
export { isProblemBody, parseProblem } from "./runtime/problem";
export type { ApiResult } from "./runtime/result";
export { isOk } from "./runtime/result";
export { ErrorCodes, ErrorTypes, type ErrorCode } from "./generated/errors";
