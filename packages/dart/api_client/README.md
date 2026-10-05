# Dart SDK for the Project API

Mirrors `packages/ts/api-client`: transport abstraction, RFC 9457 problem
parsing, typed operations. Used by `apps/mobile` (Flutter). Pure Dart — no
Flutter dependency, so it is analyzed and tested with the Dart SDK alone.

| File | Origin |
|---|---|
| `lib/src/generated/errors.dart` | generated from `contracts/errors/*.yaml` |
| `lib/src/generated/models.dart` | generated from `contracts/http/openapi.yaml` (component schemas) |
| `lib/src/client.dart` | hand-written operations over the generated models |
| `lib/src/problem.dart` | hand-written tolerant Problem parsing |
| `lib/src/transport.dart`, `lib/src/result.dart` | hand-written transport port and result type |

`lib/src/generated/` is produced by `make generate` (built into
`scripts/contracts/generate.py`, no Java or external generator) and is never
hand-edited; `make check-generated` fails on drift. When the contract adds an
operation, add it to `client.dart` using the regenerated models.

This is a library package: `pubspec.lock` is not committed (the app that
consumes it, `apps/mobile`, commits its own lock).

```bash
dart pub get
dart analyze
dart test
```
