"""Dart subset: the real contract renders, and structures outside it fail."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts" / "contracts"))
from dart_subset import DartSubsetError, render_models  # noqa: E402

OPENAPI = ROOT / "contracts" / "http" / "openapi.yaml"


def _schema(body: dict) -> dict:
    return {"components": {"schemas": body}}


def test_real_contract_emits_enum_and_map() -> None:
    spec = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    text = render_models(spec)
    assert "enum HealthStatus {\n  ok,\n}" in text
    assert "enum ReadinessStatus {\n  ready,\n  not_ready,\n}" in text
    assert "final HealthStatus status;" in text
    assert "HealthStatus.values.byName(json['status'] as String)" in text
    assert "Map<String, String> checks;" in text
    assert "status.name" in text
    assert "Object?" not in text


def test_oneof_fails() -> None:
    spec = _schema({"T": {"oneOf": [{"type": "string"}, {"type": "integer"}]}})
    try:
        render_models(spec)
    except DartSubsetError as exc:
        assert "oneOf" in str(exc)
    else:
        raise AssertionError("oneOf must fail")


def test_additional_properties_true_fails() -> None:
    spec = _schema(
        {
            "T": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": True,
            }
        }
    )
    try:
        render_models(spec)
    except DartSubsetError as exc:
        assert "additionalProperties: true" in str(exc)
    else:
        raise AssertionError("additionalProperties true must fail")


def test_mixed_object_fails() -> None:
    spec = _schema(
        {
            "T": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": {"type": "string"},
            }
        }
    )
    try:
        render_models(spec)
    except DartSubsetError as exc:
        assert "together" in str(exc)
    else:
        raise AssertionError("mixed object must fail")


def test_non_date_time_format_fails() -> None:
    spec = _schema(
        {
            "T": {
                "type": "object",
                "properties": {"site": {"type": "string", "format": "uri"}},
            }
        }
    )
    try:
        render_models(spec)
    except DartSubsetError as exc:
        assert "uri" in str(exc)
    else:
        raise AssertionError("format uri must fail")


def test_non_identifier_enum_fails() -> None:
    spec = _schema(
        {
            "T": {
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["not-ready"]}},
            }
        }
    )
    try:
        render_models(spec)
    except DartSubsetError as exc:
        assert "not-ready" in str(exc)
    else:
        raise AssertionError("non-identifier enum must fail")


def test_nullable_keyword_and_type_array_fail() -> None:
    nullable = _schema(
        {"T": {"type": "object", "properties": {"name": {"type": "string", "nullable": True}}}}
    )
    union = _schema({"T": {"type": "object", "properties": {"name": {"type": ["string", "null"]}}}})
    for spec in (nullable, union):
        try:
            render_models(spec)
        except DartSubsetError:
            continue
        raise AssertionError("null forms must fail")
