/// Typed API client. Wire models are generated from contracts/http/openapi.yaml
/// into ../generated/models.dart — this file holds operations only.
library;

import 'dart:convert';

import 'generated/models.dart';
import 'problem.dart';
import 'result.dart';
import 'transport.dart';

typedef TokenProvider = String? Function();

class ApiClient {
  final Transport _transport;
  final String baseUrl;
  final TokenProvider? tokenProvider;
  final Duration timeout;

  ApiClient({
    required Transport transport,
    this.baseUrl = '',
    this.tokenProvider,
    this.timeout = const Duration(seconds: 15),
  }) : _transport = transport;

  Future<ApiResult<T>> _request<T>(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
    Map<String, String>? headers,
    required T Function(Map<String, dynamic>) parse,
  }) async {
    final qp = query?.entries.map((e) => '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}').join('&');
    final fullPath = '$baseUrl$path${qp != null && qp.isNotEmpty ? '?$qp' : ''}';
    final h = <String, String>{'Accept': 'application/json', ...?headers};
    final token = tokenProvider?.call();
    if (token != null) h['Authorization'] = 'Bearer $token';
    final bodyStr = body == null ? null : jsonEncode(body);
    if (bodyStr != null) h['Content-Type'] = 'application/json';

    late ApiResponse res;
    try {
      res = await _transport.send(ApiRequest(
        method: method, path: fullPath, headers: h, body: bodyStr, timeout: timeout,
      ));
    } on TransportCancelled {
      return const Cancelled();
    } catch (e) {
      return TransportFailure(e.toString());
    }

    if (res.status == 204) return Ok(null as T);

    if (res.status >= 400) {
      final problem = Problem.tryParse(res.body);
      if (problem != null) return RemoteProblem(problem);
    }
    if (res.status >= 200 && res.status < 300) {
      try {
        return Ok(parse(jsonDecode(res.body) as Map<String, dynamic>));
      } catch (e) {
        return ProtocolFailure('invalid JSON on $method $path: $e');
      }
    }
    return ProtocolFailure('unexpected status ${res.status} on $method $path');
  }

  Future<ApiResult<Health>> getHealth() => _request(
        'GET', '/api/v1/health', parse: Health.fromJson,
      );

  Future<ApiResult<ResourceList>> listResources({int page = 1, int pageSize = 20}) => _request(
        'GET', '/api/v1/resources',
        query: {'page': '$page', 'page_size': '$pageSize'},
        parse: ResourceList.fromJson,
      );

  Future<ApiResult<Resource>> createResource(String name, {String? idempotencyKey}) => _request(
        'POST', '/api/v1/resources',
        body: ResourceCreate(name: name).toJson(),
        headers: idempotencyKey == null ? null : {'Idempotency-Key': idempotencyKey},
        parse: Resource.fromJson,
      );

  Future<ApiResult<Resource>> getResource(String id) => _request(
        'GET', '/api/v1/resources/${Uri.encodeComponent(id)}', parse: Resource.fromJson,
      );

  Future<ApiResult<void>> deleteResource(String id) async {
    final r = await _request<Object?>(
      'DELETE', '/api/v1/resources/${Uri.encodeComponent(id)}', parse: (_) => null,
    );
    return switch (r) {
      Ok() => const Ok(null),
      RemoteProblem(:final problem) => RemoteProblem(problem),
      TransportFailure(:final message) => TransportFailure(message),
      ProtocolFailure(:final message) => ProtocolFailure(message),
      Cancelled() => const Cancelled(),
    };
  }
}
