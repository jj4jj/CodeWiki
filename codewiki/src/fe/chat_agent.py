#!/usr/bin/env python3
"""
Doc page chat agent service.

Provides a pydantic-ai powered CodeWikiAgent with read-only code/doc access
and a bash tool executed in a constrained session workspace.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from codewiki.src.utils import file_manager
from .config import WebAppConfig
from .github_processor import GitHubRepoProcessor


def _clip_text(value: str, max_chars: int = 12_000) -> str:
    if len(value) <= max_chars:
        return value
    omitted = len(value) - max_chars
    return f"{value[:max_chars]}\n\n... [truncated {omitted} chars]"


def _normalize_relpath(raw_path: str) -> str:
    normalized = (raw_path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _resolve_under(base: Path, rel_path: str) -> Path:
    candidate = (base / _normalize_relpath(rel_path)).resolve()
    if not candidate.is_relative_to(base.resolve()):
        raise ValueError("Path escapes allowed workspace")
    return candidate


@dataclass
class _ChatSession:
    session_id: str
    job_id: str
    repo_url: str
    docs_dir: Path
    current_page: str
    created_at: datetime
    updated_at: datetime
    sandbox_root: Path
    workspace_dir: Path
    repo_dir: Optional[Path] = None
    temp_user: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    model_name: str = ""


@dataclass
class _ChatDeps:
    service: "CodeWikiChatService"
    session: _ChatSession


async def _list_docs_tool(ctx: RunContext[_ChatDeps], subpath: str = "", limit: int = 200) -> str:
    docs_root = ctx.deps.session.docs_dir
    target = _resolve_under(docs_root, subpath or ".")
    if not target.exists():
        return f"Path not found: {target}"
    if target.is_file():
        return str(target.relative_to(docs_root))

    rows: list[str] = []
    for path in sorted(target.rglob("*")):
        if len(rows) >= max(1, limit):
            break
        rel = path.relative_to(docs_root).as_posix()
        prefix = "d" if path.is_dir() else "f"
        rows.append(f"[{prefix}] {rel}")
    if not rows:
        return "No files found"
    return "\n".join(rows)


async def _read_doc_tool(ctx: RunContext[_ChatDeps], relative_path: str) -> str:
    docs_root = ctx.deps.session.docs_dir
    target = _resolve_under(docs_root, relative_path)
    if not target.exists() or not target.is_file():
        return f"Document not found: {relative_path}"
    if target.suffix.lower() not in {".md", ".txt", ".json"}:
        return f"Unsupported doc file type: {target.suffix}"
    return _clip_text(file_manager.load_text(target), WebAppConfig.CHAT_MAX_TOOL_OUTPUT_CHARS)


async def _list_code_tool(ctx: RunContext[_ChatDeps], subpath: str = "", limit: int = 400) -> str:
    repo_root = ctx.deps.session.repo_dir
    if not repo_root or not repo_root.exists():
        return "Code repository is unavailable for this chat session."

    target = _resolve_under(repo_root, subpath or ".")
    if not target.exists():
        return f"Path not found: {target}"
    if target.is_file():
        return str(target.relative_to(repo_root))

    rows: list[str] = []
    for path in sorted(target.rglob("*")):
        if len(rows) >= max(1, limit):
            break
        rel = path.relative_to(repo_root).as_posix()
        prefix = "d" if path.is_dir() else "f"
        rows.append(f"[{prefix}] {rel}")
    if not rows:
        return "No files found"
    return "\n".join(rows)


async def _read_code_tool(
    ctx: RunContext[_ChatDeps],
    relative_path: str,
    start_line: int = 1,
    end_line: int = 220,
) -> str:
    repo_root = ctx.deps.session.repo_dir
    if not repo_root or not repo_root.exists():
        return "Code repository is unavailable for this chat session."

    target = _resolve_under(repo_root, relative_path)
    if not target.exists() or not target.is_file():
        return f"Code file not found: {relative_path}"

    text = file_manager.load_text(target)
    lines = text.splitlines()
    line_count = len(lines)
    lo = max(1, start_line)
    hi = min(max(lo, end_line), line_count)
    selected = lines[lo - 1 : hi]
    numbered = [f"{idx + lo:>5} | {line}" for idx, line in enumerate(selected)]
    payload = "\n".join(numbered) if numbered else ""
    header = f"# {target.relative_to(repo_root).as_posix()} ({lo}-{hi}/{line_count})"
    return _clip_text(f"{header}\n{payload}", WebAppConfig.CHAT_MAX_TOOL_OUTPUT_CHARS)


async def _grep_code_tool(
    ctx: RunContext[_ChatDeps],
    pattern: str,
    subpath: str = "",
    limit: int = 80,
) -> str:
    repo_root = ctx.deps.session.repo_dir
    if not repo_root or not repo_root.exists():
        return "Code repository is unavailable for this chat session."

    target = _resolve_under(repo_root, subpath or ".")
    if not target.exists():
        return f"Path not found: {target}"

    regex = re.compile(pattern)
    rows: list[str] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = file_manager.load_text(path)
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel = path.relative_to(repo_root).as_posix()
                rows.append(f"{rel}:{idx}: {line.strip()}")
                if len(rows) >= max(1, limit):
                    return "\n".join(rows)
    return "\n".join(rows) if rows else "No matches found."


async def _run_bash_tool(
    ctx: RunContext[_ChatDeps],
    command: str,
    timeout_seconds: int = 20,
) -> str:
    return ctx.deps.service.run_shell_command(
        session=ctx.deps.session,
        command=command,
        timeout_seconds=timeout_seconds,
    )


class CodeWikiChatService:
    """Stateful chat service for generated documentation pages."""

    def __init__(self, background_worker, cache_manager):
        self.background_worker = background_worker
        self.cache_manager = cache_manager
        self._sessions: dict[str, _ChatSession] = {}
        self._lock = threading.RLock()
        self._provider = OpenAIProvider(
            base_url=WebAppConfig.AGENT_MODEL_BASE_URL,
            api_key=WebAppConfig.AGENT_MODEL_API_KEY,
        )

    def _build_tools(self) -> list[Tool]:
        """Build fresh tool instances for each chat agent instance."""
        return [
            Tool(
                function=_list_docs_tool,
                name="list_docs",
                description="List generated documentation files under docs directory.",
                takes_ctx=True,
            ),
            Tool(
                function=_read_doc_tool,
                name="read_doc",
                description="Read one generated documentation file by relative path.",
                takes_ctx=True,
            ),
            Tool(
                function=_list_code_tool,
                name="list_code_files",
                description="List code files inside the read-only repository snapshot.",
                takes_ctx=True,
            ),
            Tool(
                function=_read_code_tool,
                name="read_code",
                description="Read code file content by relative path and line range.",
                takes_ctx=True,
            ),
            Tool(
                function=_grep_code_tool,
                name="grep_code",
                description="Regex search across repository files with line numbers.",
                takes_ctx=True,
            ),
            Tool(
                function=_run_bash_tool,
                name="bash",
                description=(
                    "Execute linux shell command in chat workspace. "
                    "Only inspect current docs/code folders; no modifications allowed."
                ),
                takes_ctx=True,
            ),
        ]

    def _make_models(self) -> tuple[Any, str]:
        names = [name.strip() for name in WebAppConfig.AGENT_MODEL_NAMES if name and name.strip()]
        if not names:
            names = ["kimi-k2.5"]

        models = [
            OpenAIModel(
                model_name=name,
                provider=self._provider,
                settings=OpenAIModelSettings(
                    temperature=0.1,
                    max_tokens=4096,
                ),
            )
            for name in names
        ]
        primary_name = names[0]
        if len(models) == 1:
            return models[0], primary_name
        return FallbackModel(*models), primary_name

    def _load_metadata_commit(self, docs_dir: Path) -> str:
        metadata_file = docs_dir / "metadata.json"
        if not metadata_file.exists():
            return ""
        try:
            metadata = file_manager.load_json(metadata_file)
        except Exception:
            return ""
        generation = metadata.get("generation_info") if isinstance(metadata, dict) else None
        commit_id = generation.get("commit_id") if isinstance(generation, dict) else None
        return str(commit_id or "").strip()

    def _resolve_job_context(self, job_id: str) -> tuple[str, Path, str]:
        job = self.background_worker.get_job_status(job_id)
        if job and job.docs_path and Path(job.docs_path).exists():
            docs_dir = Path(job.docs_path).resolve()
            commit_id = (job.commit_id or "").strip() or self._load_metadata_commit(docs_dir)
            return job.repo_url, docs_dir, commit_id

        for entry in self.cache_manager.cache_index.values():
            if entry.job_id != job_id:
                continue
            if not entry.docs_path:
                continue
            docs_dir = Path(entry.docs_path)
            if not docs_dir.exists():
                continue
            commit_id = self._load_metadata_commit(docs_dir.resolve())
            return entry.repo_url, docs_dir.resolve(), commit_id

        raise FileNotFoundError(f"Unable to resolve job context for: {job_id}")

    def _create_temp_user(self, session_id: str) -> str:
        if os.geteuid() != 0:
            return ""

        user_suffix = hashlib.sha1(session_id.encode("utf-8")).hexdigest()[:10]
        username = f"cwchat_{user_suffix}"

        exists = subprocess.run(
            ["id", "-u", username],
            capture_output=True,
            text=True,
            check=False,
        )
        if exists.returncode == 0:
            return username

        create = subprocess.run(
            ["useradd", "-M", "-s", "/bin/sh", username],
            capture_output=True,
            text=True,
            check=False,
        )
        if create.returncode == 0:
            return username
        return ""

    def _clone_repo_readonly(self, clone_url: str, commit_id: str, target_dir: Path) -> Optional[Path]:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        success = GitHubRepoProcessor.clone_repository(clone_url, str(target_dir), commit_id or None)
        if not success:
            return None

        for root, dirs, files in os.walk(target_dir):
            for dname in dirs:
                path = Path(root) / dname
                try:
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode & ~0o222)
                except Exception:
                    pass
            for fname in files:
                path = Path(root) / fname
                try:
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode & ~0o222)
                except Exception:
                    pass

        return target_dir.resolve()

    def _create_or_get_session(
        self,
        job_id: str,
        session_id: str,
        current_page: str,
    ) -> _ChatSession:
        with self._lock:
            existing = self._sessions.get(session_id)
            if existing and existing.job_id == job_id:
                existing.updated_at = datetime.now()
                if current_page:
                    existing.current_page = current_page
                return existing

        repo_url, docs_dir, commit_id = self._resolve_job_context(job_id)
        created_at = datetime.now()
        sandbox_root = (Path(WebAppConfig.TEMP_DIR) / "chat_sessions" / session_id).resolve()
        workspace_dir = sandbox_root / "workspace"
        repo_dir = sandbox_root / "repo"

        if sandbox_root.exists():
            shutil.rmtree(sandbox_root, ignore_errors=True)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        read_only_repo = self._clone_repo_readonly(repo_url, commit_id, repo_dir)
        temp_user = self._create_temp_user(session_id)
        if temp_user and os.geteuid() == 0:
            subprocess.run(
                ["chown", "-R", f"{temp_user}:{temp_user}", str(workspace_dir)],
                capture_output=True,
                text=True,
                check=False,
            )

        _, model_name = self._make_models()

        session = _ChatSession(
            session_id=session_id,
            job_id=job_id,
            repo_url=repo_url,
            docs_dir=docs_dir,
            current_page=current_page or "overview.md",
            created_at=created_at,
            updated_at=created_at,
            sandbox_root=sandbox_root,
            workspace_dir=workspace_dir,
            repo_dir=read_only_repo,
            temp_user=temp_user,
            model_name=model_name,
        )

        with self._lock:
            self._sessions[session_id] = session
        return session

    def _cleanup_expired_sessions(self):
        ttl = timedelta(minutes=WebAppConfig.CHAT_SESSION_TTL_MINUTES)
        now = datetime.now()
        stale_ids: list[str] = []
        with self._lock:
            for session_id, session in self._sessions.items():
                if now - session.updated_at > ttl:
                    stale_ids.append(session_id)
            for session_id in stale_ids:
                session = self._sessions.pop(session_id, None)
                if not session:
                    continue
                shutil.rmtree(session.sandbox_root, ignore_errors=True)

    def run_shell_command(self, session: _ChatSession, command: str, timeout_seconds: int = 20) -> str:
        timeout = max(1, min(WebAppConfig.CHAT_SHELL_TIMEOUT_SECONDS, int(timeout_seconds)))
        cmd_text = (command or "").strip()
        if not cmd_text:
            return "Empty command."

        blocked_reason = self._check_command_policy(session, cmd_text)
        if blocked_reason:
            return f"Command blocked by policy: {blocked_reason}"

        base_command = ["sh", "-lc", cmd_text]
        if session.temp_user:
            if shutil.which("runuser"):
                base_command = ["runuser", "-u", session.temp_user, "--", "sh", "-lc", cmd_text]
            elif shutil.which("su"):
                base_command = ["su", "-s", "/bin/sh", "-c", cmd_text, session.temp_user]

        env = os.environ.copy()
        env["CODEWIKI_DOCS_DIR"] = session.docs_dir.as_posix()
        env["CODEWIKI_REPO_DIR"] = session.repo_dir.as_posix() if session.repo_dir else ""
        env["CODEWIKI_READONLY_REPO"] = "1"

        try:
            completed = subprocess.run(
                base_command,
                cwd=str(session.workspace_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s."
        except Exception as exc:
            return f"Command failed: {exc}"

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        parts = [f"$ {cmd_text}", f"exit_code={completed.returncode}"]
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(f"[stderr]\n{stderr}")
        return _clip_text("\n".join(parts), WebAppConfig.CHAT_MAX_TOOL_OUTPUT_CHARS)

    def _check_command_policy(self, session: _ChatSession, cmd_text: str) -> str:
        """Best-effort guardrail: deny write/destructive commands and off-scope paths."""
        lowered = cmd_text.lower()
        blocked_markers = [
            " rm ",
            " mv ",
            " cp ",
            " chmod ",
            " chown ",
            " sed -i",
            " git commit",
            " git push",
            " git reset",
            " git checkout",
            " tee ",
            ">>",
            ">",
            "touch ",
            "truncate ",
            "dd if=",
        ]
        wrapped = f" {lowered} "
        for marker in blocked_markers:
            if marker in wrapped:
                return f"contains forbidden operation: {marker.strip()}"

        if any(token in lowered for token in ["shutdown", "reboot", "init 0", "halt"]):
            return "contains unsafe system operation"

        allowed_prefixes = [session.workspace_dir.resolve().as_posix(), session.docs_dir.resolve().as_posix()]
        if session.repo_dir:
            allowed_prefixes.append(session.repo_dir.resolve().as_posix())

        try:
            tokens = shlex.split(cmd_text, posix=True)
        except Exception:
            tokens = []
        abs_path_re = re.compile(r"^/[^;&|]+")
        for token in tokens:
            if not token.startswith("/"):
                continue
            match = abs_path_re.match(token)
            if not match:
                continue
            path_token = match.group(0)
            if not any(path_token.startswith(prefix) for prefix in allowed_prefixes):
                return f"path outside allowed directories: {path_token}"

        return ""

    def _build_agent(self, session: _ChatSession) -> tuple[Agent, str]:
        model_chain, primary_name = self._make_models()
        docs_dir = session.docs_dir.as_posix()
        repo_dir = session.repo_dir.as_posix() if session.repo_dir else "(unavailable)"
        workspace_dir = session.workspace_dir.as_posix()
        system_prompt = (
            "你是 CodeWikiAgent（CodeDocAgent 运行时），非常熟悉目标代码库与其生成文档。\n"
            "回答规则：\n"
            "1) 默认使用中文回答（除非用户明确要求其他语言）。\n"
            "2) 先基于证据回答，不确定时必须先用工具检索文档与代码。\n"
            "3) 引用结论时给出具体相对路径与关键片段。\n\n"
            "访问边界（严格）:\n"
            f"- 仅可访问文档目录: {docs_dir}\n"
            f"- 仅可访问代码目录: {repo_dir}\n"
            f"- 命令工作目录: {workspace_dir}\n"
            "- 严禁修改任何代码/文档/权限/仓库历史。\n"
            "- 若用户要求修改，请明确拒绝并说明当前会话为只读分析模式。"
        )
        return (
            Agent(
                model_chain,
                name="CodeWikiAgent",
                deps_type=_ChatDeps,
                tools=self._build_tools(),
                system_prompt=system_prompt,
            ),
            primary_name,
        )

    def _format_prompt(
        self,
        session: _ChatSession,
        messages: list[dict[str, str]],
        user_query: str,
    ) -> str:
        history_tail = messages[-10:]
        history_lines: list[str] = []
        for item in history_tail:
            role = (item.get("role") or "user").strip().lower()
            content = (item.get("content") or "").strip()
            if not content:
                continue
            history_lines.append(f"{role.upper()}:\n{content}")

        context_lines = [
            f"job_id={session.job_id}",
            f"current_page={session.current_page}",
            f"docs_dir={session.docs_dir.as_posix()}",
            f"repo_dir={session.repo_dir.as_posix() if session.repo_dir else '(unavailable)'}",
            f"workspace_dir={session.workspace_dir.as_posix()}",
        ]
        return (
            "Context:\n"
            + "\n".join(context_lines)
            + "\n\nConversation so far:\n"
            + ("\n\n".join(history_lines) if history_lines else "(empty)")
            + "\n\nUser question:\n"
            + user_query
        )

    async def chat(
        self,
        job_id: str,
        user_query: str,
        session_id: str = "",
        current_page: str = "overview.md",
        messages: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        self._cleanup_expired_sessions()
        safe_session_id = (session_id or "").strip() or secrets.token_hex(12)
        session = self._create_or_get_session(job_id, safe_session_id, current_page=current_page)

        safe_messages = list(messages or [])
        prompt = self._format_prompt(session, safe_messages, user_query=user_query)
        agent, model_name = self._build_agent(session)

        deps = _ChatDeps(service=self, session=session)
        result = await agent.run(prompt, deps=deps)
        output = str(result.output).strip()
        if not output:
            output = "No answer generated."

        now = datetime.now()
        session.updated_at = now
        session.model_name = model_name
        session.history.append({"role": "user", "content": user_query})
        session.history.append({"role": "assistant", "content": output})

        return {
            "protocol": "a2ui-0.1",
            "session_id": session.session_id,
            "agent": "CodeWikiAgent",
            "model": model_name,
            "output": output,
            "messages": [{"role": "assistant", "content": output}],
            "events": [{"type": "assistant_message", "content": output}],
            "timestamp": now.isoformat(),
        }
