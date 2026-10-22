import pytest

from factoryagent.errors import ValidationError
from factoryagent.schema import apply_defaults, validate_params

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "count": {"type": "integer"},
        "ratio": {"type": "number"},
        "flag": {"type": "boolean"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "mode": {"type": "string", "enum": ["a", "b"], "default": "a"},
    },
    "required": ["name"],
    "additionalProperties": False,
}


def test_valid_params_pass():
    params = {"name": "x", "count": 3, "ratio": 1.5, "flag": True,
              "tags": ["u", "v"], "mode": "b"}
    assert validate_params(SCHEMA, params) == params


def test_missing_required():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, {"count": 1})


def test_wrong_type():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, {"name": "x", "count": "three"})


def test_bool_is_not_integer():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, {"name": "x", "count": True})


def test_unknown_parameter_rejected():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, {"name": "x", "surprise": 1})


def test_enum_enforced():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, {"name": "x", "mode": "zzz"})


def test_array_item_type():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, {"name": "x", "tags": ["ok", 7]})


def test_params_must_be_object():
    with pytest.raises(ValidationError):
        validate_params(SCHEMA, ["not", "a", "dict"])


def test_defaults_applied():
    out = apply_defaults(SCHEMA, {"name": "x"})
    assert out["mode"] == "a"
    assert "count" not in out
