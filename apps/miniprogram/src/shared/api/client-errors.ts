/**
 * Centralized error-code → user-facing copy (blueprint 03 §8, 07 §5).
 * ONE place for copy; pages branch on codes, never on text.
 */
import { ErrorCodes, type ErrorCode } from "@project/api-client";

const COPY: Record<ErrorCode, string> = {
  "AUTHN.REQUIRED": "请先登录",
  "AUTHN.INVALID": "登录已过期，请重新登录",
  "AUTHZ.DENIED": "没有权限执行此操作",
  "NOT.FOUND": "内容不存在",
  "VALIDATION.FAILED": "请求有误，请检查输入",
  "RATE.LIMITED": "操作太频繁，请稍后再试",
  "INTERNAL": "服务开小差了，请稍后再试",
  "CATALOG.RESOURCE_LOCKED": "资源已锁定，无法操作",
};

export function errorCopy(code: string): string {
  if (code in COPY) return COPY[code as ErrorCode];
  return COPY["INTERNAL"];
}

export { ErrorCodes };
