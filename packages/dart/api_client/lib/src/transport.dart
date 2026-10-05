/// Platform-agnostic transport contract. Mirrors packages/ts/api-client.
///
/// Pure data in, pure data out. The Flutter app injects an adapter based on
/// package:http (see apps/mobile). Cancellation: adapters throw
/// [TransportCancelled]; the client maps it to [ApiResult.cancelled].
library;

class ApiRequest {
  final String method;
  final String path;
  final Map<String, String> headers;
  final String? body;
  final Duration timeout;

  const ApiRequest({
    required this.method,
    required this.path,
    this.headers = const {},
    this.body,
    this.timeout = const Duration(seconds: 15),
  });
}

class ApiResponse {
  final int status;
  final Map<String, String> headers;
  final String body;

  const ApiResponse({required this.status, this.headers = const {}, this.body = ''});
}

abstract class Transport {
  Future<ApiResponse> send(ApiRequest request);
}

/// Thrown by adapters when the caller cancelled the request.
class TransportCancelled implements Exception {
  const TransportCancelled();
}
