"""Manage built-in and custom doc-type profiles used by CodeWiki."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_DOC_TYPE_PROFILES: Dict[str, Dict[str, Any]] = {
    "api": {
        "display_name": "API Documentation",
        "description": "面向接口使用者，强调 API 说明、参数与示例。",
        "prompt": "Focus on API documentation: endpoints, parameters, return types, and usage examples.",
    },
    "architecture": {
        "display_name": "Architecture Documentation",
        "description": "面向架构设计，强调模块关系、分层、依赖与数据流。",
        "prompt": "Focus on architecture documentation: system design, component relationships, and data flow.",
    },
    "user-guide": {
        "display_name": "User Guide",
        "description": "面向业务或产品使用者，强调上手步骤、场景与操作流程。",
        "prompt": "Focus on user guide documentation: how to use features, step-by-step tutorials.",
    },
    "developer": {
        "display_name": "Developer Guide",
        "description": "面向开发者，强调代码结构、扩展方式与实现细节。",
        "prompt": "Focus on developer documentation: code structure, contribution guidelines, and implementation details.",
    },
}

_STRING_FIELDS = {"display_name", "description", "prompt"}
_LIST_FIELDS = {"include_patterns", "exclude_patterns", "focus_modules", "skills"}
_INT_FIELDS = {
    "max_tokens",
    "max_token_per_module",
    "max_token_per_leaf_module",
    "max_depth",
    "concurrency",
}
_ALLOWED_FIELDS = _STRING_FIELDS | _LIST_FIELDS | _INT_FIELDS
_FILE_LOCK = threading.Lock()


def _profiles_file() -> Path:
    configured = os.getenv("CODEWIKI_DOC_TYPE_PROFILES_FILE", "").strip()
    if configured:
        return Path(configured)
    return Path("output") / "cache" / "doc_type_profiles.json"


def normalize_doc_type_name(name: Optional[str]) -> str:
    """Normalize raw doc-type name into a stable key."""
    key = (name or "").strip().lower()
    key = re.sub(r"[^a-z0-9._-]+", "-", key)
    key = re.sub(r"-{2,}", "-", key).strip("-")
    return key


def _normalize_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        items = [str(part).strip() for part in value]
    else:
        return None
    result = [part for part in items if part]
    return result or None


def _normalize_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def sanitize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize an incoming profile payload."""
    payload = profile or {}
    if "instructions" in payload and "prompt" not in payload:
        payload = dict(payload)
        payload["prompt"] = payload.get("instructions")

    cleaned: Dict[str, Any] = {}
    for key in _ALLOWED_FIELDS:
        if key not in payload:
            continue
        raw_value = payload.get(key)
        if key in _STRING_FIELDS:
            value = _normalize_str(raw_value)
        elif key in _LIST_FIELDS:
            value = _normalize_list(raw_value)
        else:
            value = _normalize_int(raw_value)
        if value is not None:
            cleaned[key] = value
    return cleaned


def _load_custom_profiles() -> Dict[str, Dict[str, Any]]:
    path = _profiles_file()
    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(content, dict):
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_name, profile in content.items():
        key = normalize_doc_type_name(raw_name)
        if not key or not isinstance(profile, dict):
            continue
        cleaned = sanitize_profile(profile)
        if cleaned:
            normalized[key] = cleaned
    return normalized


def _save_custom_profiles(profiles: Dict[str, Dict[str, Any]]) -> None:
    path = _profiles_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: sanitize_profile(v) for k, v in sorted(profiles.items())}
    payload = {k: v for k, v in payload.items() if v}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def list_doc_type_profiles() -> Dict[str, Dict[str, Any]]:
    """Return all doc-type profiles (built-in + custom override)."""
    merged = copy.deepcopy(DEFAULT_DOC_TYPE_PROFILES)
    with _FILE_LOCK:
        custom = _load_custom_profiles()

    for key, profile in custom.items():
        base = merged.get(key, {})
        merged[key] = {**base, **profile}

    out: Dict[str, Dict[str, Any]] = {}
    for key in sorted(merged):
        info = dict(merged[key])
        info["name"] = key
        info["built_in"] = key in DEFAULT_DOC_TYPE_PROFILES
        out[key] = info
    return out


def get_doc_type_profile(doc_type: Optional[str]) -> Optional[Dict[str, Any]]:
    """Get merged profile by doc-type name."""
    key = normalize_doc_type_name(doc_type)
    if not key:
        return None
    return list_doc_type_profiles().get(key)


def upsert_doc_type_profile(doc_type: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a custom doc-type profile."""
    key = normalize_doc_type_name(doc_type)
    if not key:
        raise ValueError("doc_type is required")
    cleaned = sanitize_profile(profile)
    if not cleaned:
        raise ValueError("profile is empty")

    with _FILE_LOCK:
        try:
            custom = _load_custom_profiles()
            custom[key] = cleaned
            _save_custom_profiles(custom)
        except Exception as exc:
            raise ValueError(f"failed to save doc type profile: {exc}")

    updated = get_doc_type_profile(key)
    if not updated:
        raise ValueError("failed to persist doc type profile")
    return updated


def delete_doc_type_profile(doc_type: str) -> bool:
    """
    Delete a custom doc-type profile override.

    Built-in profiles are not removed; deleting an override restores built-in defaults.
    """
    key = normalize_doc_type_name(doc_type)
    if not key:
        return False
    with _FILE_LOCK:
        try:
            custom = _load_custom_profiles()
            if key not in custom:
                return False
            custom.pop(key, None)
            _save_custom_profiles(custom)
        except Exception as exc:
            raise ValueError(f"failed to delete doc type profile: {exc}")
    return True
