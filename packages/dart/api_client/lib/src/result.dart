/// Client failure protocol. Callers branch on the subtype,
/// never on English detail text.
library;

import 'problem.dart';

sealed class ApiResult<T> {
  const ApiResult();
}

class Ok<T> extends ApiResult<T> {
  final T value;
  const Ok(this.value);
}

class RemoteProblem<T> extends ApiResult<T> {
  final Problem problem;
  const RemoteProblem(this.problem);
}

class TransportFailure<T> extends ApiResult<T> {
  final String message;
  const TransportFailure(this.message);
}

class ProtocolFailure<T> extends ApiResult<T> {
  final String message;
  const ProtocolFailure(this.message);
}

class Cancelled<T> extends ApiResult<T> {
  const Cancelled();
}
