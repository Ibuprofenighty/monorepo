import 'dart:convert';

import 'package:test/test.dart';

import 'package:project_api_client/api_client.dart';

class _FakeTransport extends Transport {
  final ApiResponse Function(ApiRequest) respond;
  ApiRequest? last;
  _FakeTransport(this.respond);

  @override
  Future<ApiResponse> send(ApiRequest request) async {
    last = request;
    return respond(request);
  }
}

ApiResponse _json(Object body, [int status = 200]) => ApiResponse(
      status: status,
      headers: {'content-type': 'application/json'},
      body: jsonEncode(body),
    );

void main() {
  test('parses health', () async {
    final t = _FakeTransport(
        (_) => _json({'status': 'ok', 'version': '1.0.0'}));
    final r = await ApiClient(transport: t).getHealth();
    expect(r, isA<Ok<Health>>());
    expect((r as Ok<Health>).value.version, '1.0.0');
  });

  test('encodes list query params', () async {
    final t = _FakeTransport((req) => _json({
          'items': [],
          'total': 0,
          'page': 2,
          'page_size': 5,
        }));
    await ApiClient(transport: t).listResources(page: 2, pageSize: 5);
    expect(t.last!.path, contains('page=2'));
    expect(t.last!.path, contains('page_size=5'));
  });

  test('maps problem to RemoteProblem with public code', () async {
    final t = _FakeTransport((_) => const ApiResponse(
          status: 409,
          headers: {'content-type': 'application/problem+json'},
          body: '{"type":"https://api.example.com/problems/catalog/resource-locked",'
              '"title":"Resource is locked","status":409,'
              '"code":"CATALOG.RESOURCE_LOCKED","trace_id":"t"}',
        ));
    final r = await ApiClient(transport: t).deleteResource('res_1');
    expect(r, isA<RemoteProblem<void>>());
    expect((r as RemoteProblem<void>).problem.code, 'CATALOG.RESOURCE_LOCKED');
  });

  test('204 delete is Ok', () async {
    final t = _FakeTransport(
        (_) => const ApiResponse(status: 204, body: ''));
    final r = await ApiClient(transport: t).deleteResource('res_1');
    expect(r, isA<Ok<void>>());
  });

  test('transport throw becomes TransportFailure', () async {
    final t = _FakeTransport((_) => throw Exception('down'));
    final r = await ApiClient(transport: t).getHealth();
    expect(r, isA<TransportFailure<Health>>());
  });

  test('bearer token attached', () async {
    final t = _FakeTransport(
        (_) => _json({'status': 'ok', 'version': '1'}));
    await ApiClient(transport: t, tokenProvider: () => 'tok').getHealth();
    expect(t.last!.headers['Authorization'], 'Bearer tok');
  });
}
