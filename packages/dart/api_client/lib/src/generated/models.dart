// AUTO-GENERATED from contracts/http/openapi.yaml — do not edit.
// Wire models only. Client operations live in ../../client.dart.
// minLength/maxLength/minimum/maximum/pattern are not re-checked in Dart.

enum HealthStatus {
  ok,
}

enum ReadinessStatus {
  ready,
  not_ready,
}

class Health {
  final HealthStatus status;
  final String version;
  Health({
    required this.status,
    required this.version,
  });
  factory Health.fromJson(Map<String, dynamic> json) => Health(
    status: HealthStatus.values.byName(json['status'] as String),
    version: json['version'] as String,
  );
  Map<String, dynamic> toJson() => {
    'status': status.name,
    'version': version,
  };
}

class Readiness {
  final ReadinessStatus status;
  final Map<String, String> checks;
  Readiness({
    required this.status,
    required this.checks,
  });
  factory Readiness.fromJson(Map<String, dynamic> json) => Readiness(
    status: ReadinessStatus.values.byName(json['status'] as String),
    checks: (json['checks'] as Map<String, dynamic>).map((k, e) => MapEntry(k, e as String)),
  );
  Map<String, dynamic> toJson() => {
    'status': status.name,
    'checks': checks,
  };
}

class Resource {
  final String id;
  final String name;
  final bool locked;
  final DateTime createdAt;
  Resource({
    required this.id,
    required this.name,
    required this.locked,
    required this.createdAt,
  });
  factory Resource.fromJson(Map<String, dynamic> json) => Resource(
    id: json['id'] as String,
    name: json['name'] as String,
    locked: json['locked'] as bool,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'locked': locked,
    'created_at': createdAt.toIso8601String(),
  };
}

class ResourceCreate {
  final String name;
  ResourceCreate({
    required this.name,
  });
  factory ResourceCreate.fromJson(Map<String, dynamic> json) => ResourceCreate(
    name: json['name'] as String,
  );
  Map<String, dynamic> toJson() => {
    'name': name,
  };
}

class ResourceList {
  final List<Resource> items;
  final int total;
  final int page;
  final int pageSize;
  ResourceList({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });
  factory ResourceList.fromJson(Map<String, dynamic> json) => ResourceList(
    items: ((json['items'] as List).map((e) => Resource.fromJson(e as Map<String, dynamic>)).toList()),
    total: (json['total'] as num).toInt(),
    page: (json['page'] as num).toInt(),
    pageSize: (json['page_size'] as num).toInt(),
  );
  Map<String, dynamic> toJson() => {
    'items': items.map((e) => e.toJson()).toList(),
    'total': total,
    'page': page,
    'page_size': pageSize,
  };
}
