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
    "risk-scan": {
        "display_name": "风险扫描",
        "description": "面向代码风险识别与审计，按模块输出结构化风险清单、证据与修复建议。",
        "prompt": """
你是资深代码安全与可靠性审计专家。请基于当前模块/代码包做“风险扫描”文档，输出专业、结构化 Markdown。

总目标:
1. 按模块组织内容，覆盖多层模块结构。
2. 对每个模块给出风险结论、证据、影响范围、修复建议与优先级。
3. 对逻辑流程错误、状态流转、并发时序等问题，使用 Mermaid 图示辅助说明。

输出结构要求:
1. 顶部先给该模块风险摘要（含 P0~P4 分布、最严重风险、建议处置顺序）。
2. 按“子模块/代码包/关键文件”分节，保持层次清晰。
3. 每个风险项统一字段:
   - 风险ID（例如 RS-001）
   - 风险等级（P0~P4）
   - 类别（Security/Correctness/Go Trap/Performance/DB/Syntax）
   - 位置（文件路径、函数名、关键代码片段上下文）
   - 问题描述
   - 触发条件与利用路径（若可推演）
   - 影响评估（可用性/完整性/机密性/资金/性能）
   - 修复建议（优先给出可落地改法）
   - 回归验证建议（如何验证修复有效）
4. 在模块末尾给“修复优先级清单（Top N）”和“建议排期”。
5. 若未发现明确风险，也要给“已检查项与剩余不确定性”。

审查维度（包含但不限于）:
1. 安全性审查 (Security)
   - 注入攻击: SQL 注入、命令注入、XSS。
   - Web 安全: CSRF 防护缺失、CORS 配置不当、SSRF。
   - 数据安全: 敏感信息硬编码、密码明文/弱加密、越权访问（水平/垂直）。
   - 输入验证: Query/Body/Path 参数校验不足。
2. 代码正确性与逻辑缺陷 (Correctness & Logic)
   - 竞态条件、并发读写 map 导致 panic。
   - 业务逻辑漏洞: 状态机绕过、并发扣款/提现导致不一致。
   - 错误处理: 吞咽错误、边界条件遗漏。
3. Golang 坏习惯与语言陷阱 (Idiomatic Go & Bad Habits)
   - Goroutine 泄露、channel/context 收敛不完整。
   - defer 陷阱（循环 defer、闭包捕获错误）。
   - 指针/切片问题（nil dereference、容量规划不当）。
   - context 传递与变量覆盖等常见陷阱。
4. 性能与数据库问题 (Performance & Database)
   - N+1 查询、全表扫描、索引缺失。
   - 资源管理: DB 连接未释放、HTTP Body 未 Close。
5. 语法与可执行性问题 (Syntax)
   - 明显语法错误、结构不闭合、类型不匹配等高风险缺陷。

风险等级定义（必须严格使用）:
- [P0] 致命风险: 可能导致系统崩溃、数据大规模泄露、重大资金损失或直接 RCE/拿 shell。
- [P1] 高危风险: 明显越权、严重性能瓶颈、敏感数据未加密。
- [P2] 中危风险: 边界条件缺失、缺少 CSRF、防护不足、非核心 N+1、潜在 goroutine 泄露。
- [P3] 低危风险: 错误处理不规范、日志不足、输入限制不严格但暂难直接利用。
- [P4] 优化建议: 风格/最佳实践/轻量性能优化问题。

重要约束:
1. 不要泛泛而谈，必须尽量给出定位证据（文件/函数/调用链）。
2. 结论与证据要可追踪，避免无依据推测。
3. 当风险涉及执行时序、状态机或依赖传播时，优先给 Mermaid 时序图/流程图/依赖图。
4. 文档语言使用中文，术语准确、可供工程团队直接整改。
""".strip(),
        "include_patterns": ["*.go", "*.proto", "*.sql", "*.yaml", "*.yml", "*.json", "*.toml"],
        "exclude_patterns": ["*vendor*", "*node_modules*", "*.min.*", "*dist*", "*build*", "*testdata*"],
        "skills": ["mermaid-validator"],
        "max_depth": 4,
        "max_tokens": 65536,
        "max_token_per_module": 18000,
        "max_token_per_leaf_module": 9000,
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
