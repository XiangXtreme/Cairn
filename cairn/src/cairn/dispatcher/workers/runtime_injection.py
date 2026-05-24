from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from pathlib import PurePath

from cairn.dispatcher.config import WorkerConfig
from cairn.dispatcher.runtime.manager import RuntimeManager

LOG = logging.getLogger(__name__)

_PROVIDER_SPEC_ENV = "CAIRN_PROVIDER_SPEC"
_MCP_SERVERS_ENV = "CAIRN_MCP_SERVERS"
_SKILLS_ENV = "CAIRN_SKILLS"


def prepare_worker_runtime_files(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
) -> dict[str, str]:
    env_updates: dict[str, str] = {}
    provider_spec = _load_json_env(worker.env.get(_PROVIDER_SPEC_ENV))
    mcp_servers = _load_json_env(worker.env.get(_MCP_SERVERS_ENV), default=[])
    skills = _load_json_env(worker.env.get(_SKILLS_ENV), default=[])

    provider_path = runtime_manager.write_text_file(
        workspace_name,
        f".cairn/providers/{worker.name}.json",
        json.dumps(provider_spec, ensure_ascii=False, indent=2),
    )
    env_updates["CAIRN_PROVIDER_SPEC_PATH"] = provider_path

    mcp_path = runtime_manager.write_text_file(
        workspace_name,
        f".cairn/mcp/{worker.name}.json",
        json.dumps(mcp_servers, ensure_ascii=False, indent=2),
    )
    env_updates["CAIRN_MCP_SERVERS_PATH"] = mcp_path

    skills_path = runtime_manager.write_text_file(
        workspace_name,
        f".cairn/skills/{worker.name}.json",
        json.dumps(skills, ensure_ascii=False, indent=2),
    )
    env_updates["CAIRN_SKILLS_PATH"] = skills_path

    skill_paths = _materialize_skill_directories(runtime_manager, workspace_name, worker, skills)
    if skill_paths:
        env_updates["CAIRN_SKILL_PATHS"] = ":".join(skill_paths)

    if worker.type == "codex":
        codex_home = _prepare_codex_home(
            runtime_manager,
            workspace_name,
            worker,
            provider_spec,
            mcp_servers,
            skills,
        )
        env_updates["HOME"] = codex_home
        env_updates["CODEX_HOME"] = codex_home
    elif worker.type == "claudecode":
        claude_home = _prepare_claude_home(runtime_manager, workspace_name, worker, mcp_servers, skills)
        env_updates["HOME"] = claude_home
        env_updates["CLAUDE_CONFIG_DIR"] = claude_home

    return env_updates


def _load_json_env(raw: str | None, default: object | None = None):
    if raw is None or not str(raw).strip():
        return {} if default is None else default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {} if default is None else default


def _extract_skill_paths(skills: object) -> list[str]:
    if not isinstance(skills, list):
        return []
    paths: list[str] = []
    for item in skills:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if path:
            paths.append(path)
    return paths


def _materialize_skill_directories(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
    skills: object,
) -> list[str]:
    if not isinstance(skills, list):
        return []
    paths: list[str] = []
    for item in skills:
        if not isinstance(item, dict):
            continue
        source_path = str(item.get("path", "")).strip()
        skill_id = str(item.get("id", "")).strip() or "skill"
        if not source_path:
            continue
        resolved_source_path = _resolve_visible_skill_source_path(source_path)
        try:
            target_path = runtime_manager.copy_directory(
                workspace_name,
                resolved_source_path,
                str(PurePath(".cairn") / "skills-src" / worker.name / skill_id),
            )
        except Exception as exc:
            LOG.warning(
                "failed to materialize skill directory workspace=%s worker=%s skill=%s source=%s resolved_source=%s error=%s",
                workspace_name,
                worker.name,
                skill_id,
                source_path,
                resolved_source_path,
                exc,
            )
            continue
        item["source_path"] = source_path
        item.setdefault("original_path", source_path)
        item["visible_source_path"] = resolved_source_path
        item["runtime_path"] = target_path
        item["path"] = target_path
        paths.append(target_path)
    return paths


def _prepare_codex_home(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
    provider_spec: object,
    mcp_servers: object,
    skills: object,
) -> str:
    codex_home = str(runtime_manager.workspace_path(workspace_name) / ".cairn" / "codex-home" / worker.name)
    if not isinstance(provider_spec, dict):
        provider_spec = {}
    if not isinstance(mcp_servers, list):
        mcp_servers = []

    model = str(provider_spec.get("model", worker.env.get("CODEX_MODEL", ""))).strip()
    base_url = str(provider_spec.get("base_url", worker.env.get("CODEX_BASE_URL", ""))).strip()
    provider_name = str(provider_spec.get("id", "cairn")).strip() or "cairn"

    lines = [
        f'model_provider = "{provider_name}"',
        f'model = "{_toml_escape(model)}"' if model else '',
        'disable_response_storage = true',
        'model_reasoning_effort = "high"',
        '',
        f'[model_providers."{_toml_escape(provider_name)}"]',
        f'name = "{_toml_escape(provider_name)}"',
        'wire_api = "responses"',
        'env_key = "OPENAI_API_KEY"',
        'requires_openai_auth = true',
        f'base_url = "{_toml_escape(base_url)}"' if base_url else '',
        '',
    ]

    for server in mcp_servers:
        if not isinstance(server, dict):
            continue
        server_id = str(server.get("id", "")).strip()
        if not server_id:
            continue
        lines.append(f'[mcp_servers."{_toml_escape(server_id)}"]')
        transport = str(server.get("transport", "")).strip()
        if transport == "stdio":
            command = str(server.get("command", "")).strip()
            args = server.get("args", [])
            if command:
                lines.append(f'command = "{_toml_escape(command)}"')
            if isinstance(args, list):
                rendered = ", ".join(f'"{_toml_escape(str(item))}"' for item in args if str(item).strip())
                lines.append(f"args = [{rendered}]")
        elif transport == "http":
            url = str(server.get("url", "")).strip()
            if url:
                lines.append(f'url = "{_toml_escape(url)}"')
        env = server.get("env", {})
        if isinstance(env, dict) and env:
            lines.append(f'[mcp_servers."{_toml_escape(server_id)}".env]')
            for key, value in env.items():
                key_text = str(key).strip()
                if not key_text:
                    continue
                lines.append(f'{key_text} = "{_toml_escape(str(value))}"')
        lines.append("")

    runtime_manager.write_text_file(
        workspace_name,
        str(PurePath(".cairn") / "codex-home" / worker.name / "config.toml"),
        "\n".join(line for line in lines if line is not None) + "\n",
    )
    shared_sessions_dir = _codex_sessions_dir(runtime_manager, workspace_name, worker)
    if shared_sessions_dir:
        runtime_manager.link_or_copy_directory(
            workspace_name,
            str(PurePath(".cairn") / "codex-home" / worker.name / "sessions"),
            shared_sessions_dir,
        )
    _materialize_app_skill_views(
        runtime_manager,
        workspace_name,
        worker,
        skills,
        [
            PurePath(".cairn") / "codex-home" / worker.name / "skills",
            PurePath(".cairn") / "codex-home" / worker.name / ".agents" / "skills",
        ],
    )
    return codex_home


def _codex_sessions_dir(runtime_manager: RuntimeManager, workspace_name: str, worker: WorkerConfig) -> str:
    configured = str(worker.env.get("CODEX_SESSIONS_DIR", "")).strip()
    if configured:
        return configured
    workspace_path = runtime_manager.workspace_path(workspace_name)
    if isinstance(workspace_path, Path):
        return ""
    return "/cairn-observer-sessions/.codex/sessions"


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _prepare_claude_home(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
    mcp_servers: object,
    skills: object,
) -> str:
    claude_home = str(runtime_manager.workspace_path(workspace_name) / ".cairn" / "claude-home" / worker.name)
    if not isinstance(mcp_servers, list):
        mcp_servers = []

    payload: dict[str, object] = {"mcpServers": {}}
    servers = payload["mcpServers"]
    assert isinstance(servers, dict)
    for server in mcp_servers:
        if not isinstance(server, dict):
            continue
        server_id = str(server.get("id", "")).strip()
        if not server_id:
            continue
        entry: dict[str, object] = {}
        transport = str(server.get("transport", "")).strip()
        if transport == "stdio":
            command = str(server.get("command", "")).strip()
            args = server.get("args", [])
            if command:
                entry["command"] = command
            if isinstance(args, list):
                entry["args"] = [str(item) for item in args if str(item).strip()]
        elif transport == "http":
            url = str(server.get("url", "")).strip()
            if url:
                entry["url"] = url
        env = server.get("env", {})
        if isinstance(env, dict) and env:
            entry["env"] = {str(key): str(value) for key, value in env.items() if str(key).strip()}
        servers[server_id] = entry

    runtime_manager.write_text_file(
        workspace_name,
        str(PurePath(".cairn") / "claude-home" / worker.name / ".claude.json"),
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    runtime_manager.write_text_file(
        workspace_name,
        str(PurePath(".cairn") / "claude-home" / worker.name / ".claude" / "settings.json"),
        json.dumps({"skipIntroduction": True}, ensure_ascii=False, indent=2),
    )
    shared_projects_dir = _claude_shared_dir(runtime_manager, workspace_name, worker, "projects")
    shared_sessions_dir = _claude_shared_dir(runtime_manager, workspace_name, worker, "sessions")
    shared_backups_dir = _claude_shared_dir(runtime_manager, workspace_name, worker, "backups")
    for relative_path, shared_target in (
        (PurePath(".cairn") / "claude-home" / worker.name / "projects", shared_projects_dir),
        (PurePath(".cairn") / "claude-home" / worker.name / "sessions", shared_sessions_dir),
        (PurePath(".cairn") / "claude-home" / worker.name / "backups", shared_backups_dir),
    ):
        if not shared_target:
            continue
        runtime_manager.link_or_copy_directory(
            workspace_name,
            str(relative_path),
            shared_target,
        )
    _materialize_app_skill_views(
        runtime_manager,
        workspace_name,
        worker,
        skills,
        [
            PurePath(".cairn") / "claude-home" / worker.name / ".claude" / "skills",
            PurePath(".cairn") / "claude-home" / worker.name / ".agents" / "skills",
        ],
    )
    return claude_home


def _claude_shared_dir(runtime_manager: RuntimeManager, workspace_name: str, worker: WorkerConfig, leaf: str) -> str:
    configured = str(worker.env.get("CLAUDE_PROJECTS_DIR", "")).strip()
    if configured and leaf == "projects":
        return configured
    workspace_path = runtime_manager.workspace_path(workspace_name)
    if isinstance(workspace_path, Path):
        return ""
    return f"/cairn-observer-sessions/.claude/{leaf}"


def _materialize_app_skill_views(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
    skills: object,
    base_dirs: list[PurePath],
) -> None:
    if not isinstance(skills, list):
        return
    for item in skills:
        if not isinstance(item, dict):
            continue
        source_path = str(item.get("source_path") or item.get("original_path") or item.get("path") or "").strip()
        skill_id = str(item.get("id", "")).strip() or "skill"
        if not source_path:
            continue
        item.setdefault("original_path", source_path)
        resolved_source_path = _resolve_visible_skill_source_path(source_path)
        for base_dir in base_dirs:
            try:
                runtime_manager.copy_directory(
                    workspace_name,
                    resolved_source_path,
                    str(base_dir / skill_id),
                )
            except Exception as exc:
                LOG.warning(
                    "failed to materialize app skill view workspace=%s worker=%s skill=%s source=%s resolved_source=%s target=%s error=%s",
                    workspace_name,
                    worker.name,
                    skill_id,
                    source_path,
                    resolved_source_path,
                    base_dir / skill_id,
                    exc,
                )
                continue


def _resolve_visible_skill_source_path(source_path: str) -> str:
    source = Path(source_path).expanduser()
    if source.is_dir():
        return str(source)

    candidates: list[Path] = []
    ui_config = os.getenv("CAIRN_UI_DISPATCH_CONFIG", "").strip()
    if ui_config:
        ui_root = Path(ui_config).expanduser().parent
        candidates.extend(_remap_data_dir_suffix(source_path, ui_root))
        candidates.extend(_remap_named_suffix(source_path, "registry/skills", ui_root / "registry" / "skills"))

    dispatch_config = os.getenv("CAIRN_DISPATCH_CONFIG", "").strip()
    if dispatch_config:
        repo_root = Path(dispatch_config).expanduser().parent
        candidates.extend(_remap_named_suffix(source_path, "skills", repo_root / "skills"))

    candidates.extend(_remap_named_suffix(source_path, "registry/skills", Path.cwd() / "datas" / "cairn" / "registry" / "skills"))
    candidates.extend(_remap_named_suffix(source_path, "skills", Path.cwd() / "skills"))

    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)
    return source_path


def _remap_data_dir_suffix(source_path: str, data_root: Path) -> list[Path]:
    marker = "/datas/cairn/"
    normalized = source_path.replace("\\", "/")
    if marker not in normalized:
        return []
    suffix = normalized.split(marker, 1)[1].strip("/")
    return [data_root / PurePath(suffix)] if suffix else []


def _remap_named_suffix(source_path: str, marker: str, target_root: Path) -> list[Path]:
    normalized = source_path.replace("\\", "/").strip("/")
    marker = marker.strip("/")
    parts = PurePath(normalized).parts
    marker_parts = PurePath(marker).parts
    marker_len = len(marker_parts)
    for index in range(0, len(parts) - marker_len + 1):
        if parts[index : index + marker_len] == marker_parts:
            suffix = PurePath(*parts[index + marker_len :])
            return [target_root / suffix] if str(suffix) != "." else [target_root]
    return []
