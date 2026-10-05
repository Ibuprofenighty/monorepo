import 'package:project_api_client/api_client.dart';

/// Centralized error-code → user-facing copy (blueprint 03 §8, 07 §5).
/// ONE place for copy; widgets branch on codes, never on text.
const Map<String, String> _copy = {
  ErrorCodes.AUTHN_REQUIRED: '请先登录',
  ErrorCodes.AUTHN_INVALID: '登录已过期，请重新登录',
  ErrorCodes.AUTHZ_DENIED: '没有权限执行此操作',
  ErrorCodes.NOT_FOUND: '内容不存在',
  ErrorCodes.VALIDATION_FAILED: '请求有误，请检查输入',
  ErrorCodes.RATE_LIMITED: '操作太频繁，请稍后再试',
  ErrorCodes.INTERNAL: '服务开小差了，请稍后再试',
  ErrorCodes.CATALOG_RESOURCE_LOCKED: '资源已锁定，无法操作',
};

String errorCopy(String code) => _copy[code] ?? _copy[ErrorCodes.INTERNAL]!;
