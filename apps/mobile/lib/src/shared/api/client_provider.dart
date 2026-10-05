import 'package:project_api_client/api_client.dart';
import 'http_transport.dart';

/// App-wide ApiClient singleton.
///
/// Base URL is a build-time constant (dart-define), never a secret.
/// Auth tokens come from secure storage at call time via [tokenProvider].
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000', // Android emulator → host loopback
);

String? _loadToken() {
  // TODO(project-profile §8): read from flutter_secure_storage.
  return null;
}

final ApiClient api = ApiClient(
  transport: HttpTransport(),
  baseUrl: apiBaseUrl,
  tokenProvider: _loadToken,
);
