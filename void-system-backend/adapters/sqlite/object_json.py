"""Canonical encoding rules for SQLite columns that store JSON objects."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Dict, Optional


class ObjectJSONContractError(ValueError):
    """Raised when a canonical object column does not contain a JSON object."""


def decode_object(value: Any) -> Dict[str, Any]:
    """Decode a canonical object column without runtime legacy coercion."""
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        raise ObjectJSONContractError("SQLite object field must contain a JSON object")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ObjectJSONContractError("SQLite object field contains invalid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ObjectJSONContractError("SQLite object field must contain a JSON object")
    return dict(decoded)


def decode_legacy_object(
    value: Any,
    *,
    legacy_text_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Decode historical representations during one-way migration only."""
    current = value
    for _ in range(3):
        if isinstance(current, Mapping):
            return dict(current)
        if current is None:
            return {}
        if not isinstance(current, str):
            break
        text = current.strip()
        if not text:
            return {}
        try:
            current = json.loads(text)
        except json.JSONDecodeError as exc:
            if legacy_text_key:
                return {legacy_text_key: text}
            raise ObjectJSONContractError(
                "Historical object field contains unrecognized non-JSON text"
            ) from exc
    if legacy_text_key and isinstance(current, str) and current.strip():
        return {legacy_text_key: current.strip()}
    raise ObjectJSONContractError(
        "Historical object field cannot be normalized to a JSON object"
    )


def encode_object(value: Any) -> str:
    """Encode a runtime object value and reject shapes that violate the column contract."""
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise TypeError("SQLite object fields require a mapping value")
    try:
        return json.dumps(dict(value), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ObjectJSONContractError("SQLite object field is not JSON serializable") from exc


def encode_legacy_object(value: Any, *, legacy_text_key: Optional[str] = None) -> str:
    """Normalize historical object/text representations before canonical storage."""
    return json.dumps(
        decode_legacy_object(value, legacy_text_key=legacy_text_key),
        ensure_ascii=False,
        allow_nan=False,
    )
