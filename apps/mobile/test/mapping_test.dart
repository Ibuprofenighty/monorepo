import 'package:project_api_client/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:project_mobile/src/features/resources/resources_page.dart' show toVM;
import 'package:project_mobile/src/shared/api/error_copy.dart';

void main() {
  test('maps DTO to view model', () {
    final vm = toVM(Resource(
      id: '1',
      name: 'n',
      locked: false,
      createdAt: DateTime.utc(2026, 1, 1),
    ));
    expect(vm.id, '1');
    expect(vm.name, 'n');
    expect(vm.locked, isFalse);
  });

  test('centralizes error copy and falls back safely', () {
    expect(errorCopy(ErrorCodes.CATALOG_RESOURCE_LOCKED), contains('锁定'));
    expect(errorCopy('FUTURE.UNKNOWN'), errorCopy(ErrorCodes.INTERNAL));
  });
}
