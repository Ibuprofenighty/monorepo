"""Dart models for the OpenAPI 3.1 subset this repo emits.

OAS 3.1 Schema Objects are JSON Schema 2020-12. This module fails on
anything it does not have a single Dart type for. Constraint keywords that
do not change that type are accepted and not re-checked in the generated
code. `nullable` is not an OAS 3.1 keyword. `type: [T, "null"]` is the
2020-12 null form and stays outside this subset.
"""

from __future__ import annotations

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DART_RESERVED = frozenset(
    {
        "assert",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "default",
        "do",
        "else",
        "enum",
        "extends",
        "false",
        "final",
        "finally",
        "for",
        "if",
        "in",
        "index",
        "is",
        "name",
        "new",
        "null",
        "rethrow",
        "return",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "values",
        "var",
        "void",
        "while",
        "with",
    }
)

# Keywords that change the instance shape and have no Dart encoding here.
_UNSUPPORTED = frozenset(
    {
        "allOf",
        "anyOf",
        "const",
        "contains",
        "contentEncoding",
        "contentMediaType",
        "contentSchema",
        "dependentRequired",
        "dependentSchemas",
        "discriminator",
        "else",
        "if",
        "not",
        "nullable",
        "oneOf",
        "patternProperties",
        "prefixItems",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)

# JSON Schema validation keywords that do not change the Dart type.
_CONSTRAINTS = frozenset(
    {
        "exclusiveMaximum",
        "exclusiveMinimum",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "multipleOf",
        "pattern",
        "uniqueItems",
    }
)

# Annotation keywords (2020-12 annotation vocab + OAS annotations).
_ANNOTATIONS = frozenset(
    {
        "default",
        "deprecated",
        "description",
        "example",
        "examples",
        "externalDocs",
        "readOnly",
        "title",
        "writeOnly",
        "xml",
    }
)

_SHAPE = frozenset(
    {"$ref", "additionalProperties", "enum", "format", "items", "properties", "required", "type"}
)
_ALLOWED = _UNSUPPORTED | _CONSTRAINTS | _ANNOTATIONS | _SHAPE


class DartSubsetError(Exception):
    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


def render_models(openapi: dict) -> str:
    schemas: dict = openapi["components"]["schemas"]
    enums: dict[str, list[str]] = {}
    classes: list[str] = []
    for name in sorted(schemas):
        if name == "Problem":
            # Hand-written problem.dart. Its uri formats are outside this subset.
            continue
        classes.append(_render_class(name, schemas[name], schemas, enums))
    enum_blocks = [_render_enum(n, enums[n]) for n in sorted(enums)]
    lines = [
        "// AUTO-GENERATED from contracts/http/openapi.yaml — do not edit.",
        "// Wire models only. Client operations live in ../../client.dart.",
        "// minLength/maxLength/minimum/maximum/pattern are not re-checked in Dart.",
        "",
        *enum_blocks,
        *classes,
    ]
    return "\n".join(lines).rstrip() + "\n"


def _render_enum(name: str, values: list[str]) -> str:
    body = "\n".join(f"  {value}," for value in values)
    return f"enum {name} {{\n{body}\n}}\n"


def _render_class(name: str, schema: dict, schemas: dict, enums: dict[str, list[str]]) -> str:
    _check_node(name, schema, allow_closed_object=True)
    if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
        raise DartSubsetError(name, "a named schema must be type object with properties")
    if isinstance(schema.get("additionalProperties"), dict):
        raise DartSubsetError(
            name,
            "a named map (additionalProperties schema, no fixed properties) is outside the subset",
        )
    props: dict = schema["properties"]
    required = set(schema.get("required") or [])
    unknown_required = required - set(props)
    if unknown_required:
        raise DartSubsetError(name, f"required names not in properties: {sorted(unknown_required)}")

    fields: list[str] = []
    ctor: list[str] = []
    from_json: list[str] = []
    to_json: list[str] = []
    for pname, prop in props.items():
        if not isinstance(prop, dict):
            raise DartSubsetError(f"{name}.{pname}", "property schema must be an object")
        enum_name = _enum_name(name, pname) if "enum" in prop else None
        dart_t, from_expr, to_expr = _dart_type(
            f"{name}.{pname}", prop, schemas, enum_name=enum_name, enums=enums
        )
        field = _camel(pname)
        opt = "" if pname in required else "?"
        fields.append(f"  final {dart_t}{opt} {field};")
        if pname in required:
            ctor.append(f"    required this.{field},")
            expr = from_expr.format(v=f"json['{pname}']")
        else:
            ctor.append(f"    this.{field},")
            inner = from_expr.format(v=f"json['{pname}']")
            expr = f"json['{pname}'] == null ? null : {inner}"
        from_json.append(f"    {field}: {expr},")
        to_json.append(f"    '{pname}': {to_expr.format(v=field)},")

    return "\n".join(
        [
            f"class {name} {{",
            *fields,
            f"  {name}({{",
            *ctor,
            "  });",
            f"  factory {name}.fromJson(Map<String, dynamic> json) => {name}(",
            *from_json,
            "  );",
            "  Map<String, dynamic> toJson() => {",
            *to_json,
            "  };",
            "}",
            "",
        ]
    )


def _dart_type(
    path: str,
    prop: dict,
    schemas: dict,
    *,
    enum_name: str | None,
    enums: dict[str, list[str]],
) -> tuple[str, str, str]:
    """(dart type, fromJson template with {v}, toJson template with {v})."""
    _check_node(path, prop, allow_closed_object=False)
    if "$ref" in prop:
        ref = str(prop["$ref"]).split("/")[-1]
        if ref not in schemas:
            raise DartSubsetError(path, f"unresolved $ref {prop['$ref']}")
        return ref, f"{ref}.fromJson({{v}} as Map<String, dynamic>)", "{v}.toJson()"

    if "enum" in prop:
        if prop.get("type") != "string":
            raise DartSubsetError(path, "enum requires type: string")
        if enum_name is None:
            raise DartSubsetError(path, "enum is only supported on object properties")
        values = _string_enum(path, prop["enum"])
        if enum_name in enums and enums[enum_name] != values:
            raise DartSubsetError(path, f"enum name {enum_name} already used")
        enums[enum_name] = values
        return (
            enum_name,
            f"{enum_name}.values.byName({{v}} as String)",
            "{v}.name",
        )

    fmt = prop.get("format")
    if fmt is not None and fmt != "date-time":
        raise DartSubsetError(path, f"format {fmt!r} is outside the subset (only date-time)")
    t = prop.get("type")
    if isinstance(t, list):
        raise DartSubsetError(
            path, 'type arrays are outside the subset (OAS 3.1 null is type: [T, "null"])'
        )
    if fmt == "date-time":
        if t != "string":
            raise DartSubsetError(path, "format date-time requires type: string")
        return "DateTime", "DateTime.parse({v} as String)", "{v}.toIso8601String()"
    if t == "string":
        return "String", "{v} as String", "{v}"
    if t == "integer":
        return "int", "({v} as num).toInt()", "{v}"
    if t == "number":
        return "double", "({v} as num).toDouble()", "{v}"
    if t == "boolean":
        return "bool", "{v} as bool", "{v}"
    if t == "array":
        items = prop.get("items")
        if not isinstance(items, dict):
            raise DartSubsetError(path, "array requires an items schema")
        item_t, item_from, item_to = _dart_type(
            f"{path}[]", items, schemas, enum_name=None, enums=enums
        )
        return (
            f"List<{item_t}>",
            f"(({{v}} as List).map((e) => {item_from.format(v='e')}).toList())",
            f"{{v}}.map((e) => {item_to.format(v='e')}).toList()",
        )
    if t == "object":
        return _object_type(path, prop, schemas, enums)
    raise DartSubsetError(path, "schema has no supported type")


def _object_type(
    path: str, prop: dict, schemas: dict, enums: dict[str, list[str]]
) -> tuple[str, str, str]:
    props = prop.get("properties")
    ap = prop.get("additionalProperties", None)
    if isinstance(props, dict):
        raise DartSubsetError(path, "inline object properties are outside the subset; use $ref")
    if ap is True:
        raise DartSubsetError(path, "additionalProperties: true is unconstrained")
    if ap is False:
        raise DartSubsetError(path, "additionalProperties: false without properties")
    if isinstance(ap, dict):
        inner_t, inner_from, _inner_to = _dart_type(
            f"{path}.*", ap, schemas, enum_name=None, enums=enums
        )
        decoded = inner_from.format(v="e")
        from_expr = f"({{v}} as Map<String, dynamic>).map((k, e) => MapEntry(k, {decoded}))"
        return f"Map<String, {inner_t}>", from_expr, "{v}"
    raise DartSubsetError(path, "object requires properties or an additionalProperties schema")


def _check_node(path: str, schema: dict, *, allow_closed_object: bool) -> None:
    if not isinstance(schema, dict):
        raise DartSubsetError(path, "schema must be an object")
    unknown = set(schema) - _ALLOWED
    if unknown:
        raise DartSubsetError(path, f"keywords outside the subset: {sorted(unknown)}")
    hit = set(schema) & _UNSUPPORTED
    if hit:
        raise DartSubsetError(path, f"unsupported: {sorted(hit)}")
    if "$ref" in schema:
        extra = set(schema) - {"$ref"} - _ANNOTATIONS
        if extra:
            raise DartSubsetError(path, f"$ref combined with {sorted(extra)}")
        return
    ap = schema.get("additionalProperties", None)
    props = schema.get("properties")
    if ap is True:
        raise DartSubsetError(path, "additionalProperties: true is unconstrained")
    if isinstance(ap, dict) and isinstance(props, dict):
        raise DartSubsetError(
            path, "properties and additionalProperties schema together are outside the subset"
        )
    if allow_closed_object and ap is False and not isinstance(props, dict):
        raise DartSubsetError(path, "additionalProperties: false without properties")


def _string_enum(path: str, values: object) -> list[str]:
    if not isinstance(values, list) or not values:
        raise DartSubsetError(path, "enum must be a non-empty array")
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not _IDENT.fullmatch(value) or value in _DART_RESERVED:
            raise DartSubsetError(
                path, f"enum value {value!r} is not a Dart identifier (reserved words rejected)"
            )
        out.append(value)
    return out


def _enum_name(schema: str, prop: str) -> str:
    return schema + "".join(part[:1].upper() + part[1:] for part in prop.split("_"))


def _camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
