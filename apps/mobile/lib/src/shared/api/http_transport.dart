import 'package:project_api_client/api_client.dart';
import 'package:http/http.dart' as http;

/// package:http transport adapter — the ONLY file here that touches
/// package:http. Everything else talks to ApiClient.
///
/// Exceptions propagate to ApiClient, which maps them to
/// ApiResult.transportFailure. Adapters throw [TransportCancelled]
/// when the caller cancels (not wired here — no signal on ApiRequest).
class HttpTransport implements Transport {
  HttpTransport({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  @override
  Future<ApiResponse> send(ApiRequest req) async {
    final request = http.Request(req.method, Uri.parse(req.path))
      ..headers.addAll(req.headers);
    if (req.body != null) request.body = req.body!;
    final streamed = await _client.send(request).timeout(req.timeout);
    final body = await streamed.stream.bytesToString();
    return ApiResponse(
      status: streamed.statusCode,
      headers: streamed.headers,
      body: body,
    );
  }

  void close() => _client.close();
}
