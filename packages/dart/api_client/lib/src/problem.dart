/// RFC 9457 problem+json parsing. Unknown public codes are accepted,
/// never crash the client.
library;

import 'dart:convert';

class Problem {
  final String type;
  final String title;
  final int status;
  final String code;
  final String? detail;
  final String? instance;
  final String? traceId;

  const Problem({
    required this.type,
    required this.title,
    required this.status,
    required this.code,
    this.detail,
    this.instance,
    this.traceId,
  });

  static Problem? tryParse(String text) {
    try {
      final v = jsonDecode(text);
      if (v is! Map<String, dynamic>) return null;
      if (v['type'] is! String ||
          v['title'] is! String ||
          v['status'] is! int ||
          v['code'] is! String) {
        return null;
      }
      return Problem(
        type: v['type'] as String,
        title: v['title'] as String,
        status: v['status'] as int,
        code: v['code'] as String,
        detail: v['detail'] as String?,
        instance: v['instance'] as String?,
        traceId: v['trace_id'] as String?,
      );
    } catch (_) {
      return null;
    }
  }
}
