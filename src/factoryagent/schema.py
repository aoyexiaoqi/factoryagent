"""A small, dependency-free JSON-schema validator for tool parameters.

Only the subset the tool registry needs is implemented: ``type`` checks
(string / number / integer / boolean / array / object), ``required``,
``properties``, ``items``, ``enum`` and rejection of unknown properties.
This is the gate every tool call — typed by a human, extracted by the
deterministic router, or proposed by an optional LLM — must pass.
"""

from __future__ import annotations

from .errors import ValidationError

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _check_value(name, value, spec, errors):
    expected = spec.get("type")
    if expected is not None:
        check = _TYPE_CHECKS.get(expected)
        if check is None:
            errors.append("%s: unknown schema type %r" % (name, expected))
            return
        if not check(value):
            errors.append(
                "%s: expected %s, got %s" % (name, expected, type(value).__name__)
            )
            return
    if "enum" in spec and value not in spec["enum"]:
        errors.append("%s: %r is not one of %r" % (name, value, spec["enum"]))
    if expected == "array" and "items" in spec:
        for idx, item in enumerate(value):
            _check_value("%s[%d]" % (name, idx), item, spec["items"], errors)
    if expected == "object" and "properties" in spec:
        _check_object(name, value, spec, errors)


def _check_object(name, value, spec, errors):
    props = spec.get("properties", {})
    for key in spec.get("required", []):
        if key not in value:
            errors.append("%s.%s: required parameter missing" % (name, key))
    additional = spec.get("additionalProperties", False)
    for key, val in value.items():
        if key in props:
            _check_value("%s.%s" % (name, key), val, props[key], errors)
        elif additional is False:
            errors.append("%s.%s: unknown parameter" % (name, key))


def validate_params(schema, params):
    """Validate ``params`` (a dict) against a JSON-schema dict.

    Returns the params unchanged on success; raises ValidationError with a
    human-readable list of every problem otherwise.
    """
    if not isinstance(params, dict):
        raise ValidationError("parameters must be an object, got %s"
                              % type(params).__name__)
    errors = []
    _check_object("params", params, schema, errors)
    if errors:
        raise ValidationError("; ".join(errors))
    return params


def apply_defaults(schema, params):
    """Fill in schema ``default`` values for parameters that were omitted."""
    out = dict(params)
    for key, spec in schema.get("properties", {}).items():
        if key not in out and "default" in spec:
            out[key] = spec["default"]
    return out
