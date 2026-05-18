from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import base64
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException

from cairn.dispatcher.config import DispatchConfig, TaskType, WorkerType
from cairn.dispatcher.runtime.manager import create_runtime_manager
from cairn.dispatcher.tasks.common import run_healthcheck
from cairn.dispatcher.workers.registry import get_driver
from cairn.server.db import DEFAULT_DB
from cairn.server.models import (
    DispatchBootstrapTaskSettings,
    DispatchExploreTaskSettings,
    DispatchModeInfo,
    DispatchReasonTaskSettings,
    DispatchRuntimeSettings,
    DispatchSettings,
    DispatchSettingsMode,
    DispatchTaskSettings,
    DiscoveredSkill,
    DispatchWorkerSettings,
    McpServerSettings,
    ProviderSettings,
    SkillZipImportRequest,
    SkillZipImportResponse,
    SkillSettings,
    WorkerHealthcheckRequest,
    WorkerHealthcheckResponse,
    UpdateDispatchSettingsRequest,
    WorkerBindingSettings,
)

_WORKER_ENV_FIELD_MAP: dict[WorkerType, dict[str, str]] = {
    "claudecode": {
        "model": "ANTHROPIC_MODEL",
        "base_url": "ANTHROPIC_BASE_URL",
        "auth_token": "ANTHROPIC_AUTH_TOKEN",
    },
    "codex": {
        "model": "CODEX_MODEL",
        "base_url": "CODEX_BASE_URL",
        "auth_token": "OPENAI_API_KEY",
    },
    "pi": {
        "model": "PI_MODEL",
        "base_url": "PI_BASE_URL",
        "auth_token": "PI_API_KEY",
        "provider_api": "PI_PROVIDER_API",
        "context_window": "PI_MODEL_CONTEXT_WINDOW",
    },
    "mock": {},
}

_MCP_SUPPORT_MATRIX: dict[WorkerType, bool] = {
    "claudecode": True,
    "codex": True,
    "pi": False,
    "mock": False,
}
_SKILL_SUPPORT_MATRIX: dict[WorkerType, bool] = {
    "claudecode": True,
    "codex": True,
    "pi": False,
    "mock": False,
}
_TASK_TYPE_ORDER: tuple[TaskType, ...] = ("bootstrap", "reason", "explore")
_DISPATCH_SETTINGS_MODE_ENV = "CAIRN_DISPATCH_SETTINGS_MODE"
_UI_DISPATCH_CONFIG_ENV = "CAIRN_UI_DISPATCH_CONFIG"
_MCP_ENV_KEY = "CAIRN_MCP_SERVERS"
_SKILL_ENV_KEY = "CAIRN_SKILLS"
_UI_ROOT_DIRNAME = "dispatch_ui"
_WORKERS_FILENAME = "workers.json"
_PROVIDERS_FILENAME = "providers.json"
_MCP_SERVERS_FILENAME = "mcp_servers.json"
_SKILLS_FILENAME = "skills.json"
_WORKER_BINDINGS_FILENAME = "worker_bindings.json"
_SETTINGS_FILENAME = "settings.json"
_COMPILED_FILENAME = "dispatch_ui.yaml"
_VALIDATION_ERROR_FILENAME = "last_validation_error.txt"
_PROVIDER_ENV_KEY = "CAIRN_PROVIDER_SPEC"
_REGISTRY_DIRNAME = "registry"
_REGISTRY_SKILLS_DIRNAME = "skills"
_REGISTRY_MCP_DIRNAME = "mcp"
_PROVIDER_SUPPORT_MATRIX: dict[WorkerType, bool] = {
    "claudecode": True,
    "codex": True,
    "pi": True,
    "mock": False,
}

def resolve_dispatch_config_path() -> Path:
    env_value = os.getenv("CAIRN_DISPATCH_CONFIG", "").strip()
    if env_value:
        return Path(env_value)

    cwd = Path.cwd()
    for name in ("dispatch.yaml", "dispatch_docker.yaml", "dispatch_mock.yaml"):
        candidate = cwd / name
        if candidate.exists():
            return candidate
    return cwd / "dispatch.yaml"


def resolve_ui_dispatch_config_path() -> Path:
    env_value = os.getenv(_UI_DISPATCH_CONFIG_ENV, "").strip()
    if env_value:
        return Path(env_value)
    cwd_datas = Path.cwd() / "datas" / "cairn"
    if cwd_datas.parent.exists() or (Path.cwd() / "pyproject.toml").exists():
        return cwd_datas / _COMPILED_FILENAME
    return DEFAULT_DB.parent / _COMPILED_FILENAME


def resolve_ui_dispatch_root_path() -> Path:
    compiled_path = resolve_ui_dispatch_config_path()
    return compiled_path.parent / _UI_ROOT_DIRNAME


def resolve_registry_root_path() -> Path:
    compiled_path = resolve_ui_dispatch_config_path()
    return compiled_path.parent / _REGISTRY_DIRNAME


def resolve_registry_skills_root_path() -> Path:
    return resolve_registry_root_path() / _REGISTRY_SKILLS_DIRNAME


def resolve_registry_mcp_root_path() -> Path:
    return resolve_registry_root_path() / _REGISTRY_MCP_DIRNAME


def resolve_skill_scan_roots() -> tuple[Path, ...]:
    return (
        resolve_registry_skills_root_path(),
        *resolve_repo_skill_roots(),
        Path.cwd() / "datas" / "cairn-runtime" / "skills",
    )


def resolve_repo_skill_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for candidate in (
        Path.cwd() / "skills",
        Path(__file__).resolve().parents[4] / "skills",
    ):
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(candidate)
    return tuple(roots)


def resolve_dispatch_settings_mode(mode: DispatchSettingsMode | None = None) -> DispatchSettingsMode:
    if mode:
        return mode
    env_value = os.getenv(_DISPATCH_SETTINGS_MODE_ENV, "").strip().lower()
    if env_value in {"file", "ui"}:
        return env_value  # type: ignore[return-value]
    return "file"


def resolve_dispatch_settings_path(mode: DispatchSettingsMode | None = None, *, create_ui: bool = False) -> Path:
    resolved_mode = resolve_dispatch_settings_mode(mode)
    if resolved_mode == "file":
        return resolve_dispatch_config_path()
    ensure_ui_dispatch_bundle(create=create_ui)
    return resolve_ui_dispatch_config_path()


def read_dispatch_settings(mode: DispatchSettingsMode | None = None) -> DispatchSettings:
    resolved_mode = resolve_dispatch_settings_mode(mode)
    if resolved_mode == "ui":
        ensure_ui_dispatch_bundle(create=True)
        _sync_repo_skills_to_registry()

    path = resolve_dispatch_settings_path(resolved_mode, create_ui=resolved_mode == "ui")
    if not path.exists():
        raise HTTPException(404, f"Dispatch config not found: {path}")

    raw = _load_raw_config(path)
    _validate_raw_dispatch_config(raw, path)
    runtime_raw = raw.get("runtime") or {}
    workers_raw = raw.get("workers") or []

    if resolved_mode == "ui":
        ui_bundle = _read_ui_bundle()
        source_path = resolve_ui_dispatch_root_path()
        writable = _bundle_writable(source_path)
        mode_info = DispatchModeInfo(
            mode="ui",
            source_path=str(source_path),
            compiled_path=str(path),
            hot_reload_enabled=bool(ui_bundle["settings"].get("hot_reload", True)),
            compiled_updated_at=_isoformat(path),
            last_validation_error=_read_validation_error(),
        )
        mcp_servers = ui_bundle["mcp_servers"]
        providers = ui_bundle["providers"]
        skills = ui_bundle["skills"]
        worker_bindings = ui_bundle["worker_bindings"]
    else:
        writable = os.access(path, os.W_OK)
        mode_info = DispatchModeInfo(
            mode="file",
            source_path=str(path),
            compiled_path=str(path),
            hot_reload_enabled=True,
            compiled_updated_at=_isoformat(path),
            last_validation_error="",
        )
        providers = _providers_from_file_workers(workers_raw)
        mcp_servers = []
        skills = []
        worker_bindings = []

    return DispatchSettings(
        mode=resolved_mode,
        path=str(path),
        writable=writable,
        runtime=DispatchRuntimeSettings(**runtime_raw),
        tasks=_tasks_to_settings(raw.get("tasks") or {}),
        workers=[_worker_to_settings(worker, worker_bindings, providers) for worker in workers_raw],
        mode_info=mode_info,
        providers=providers,
        mcp_servers=mcp_servers,
        skills=skills,
        worker_bindings=worker_bindings,
        restart_required=False,
    )


def write_dispatch_settings(body: UpdateDispatchSettingsRequest) -> DispatchSettings:
    resolved_mode = resolve_dispatch_settings_mode(body.mode)
    if resolved_mode == "ui":
        ensure_ui_dispatch_bundle(create=True)
        bundle_root = resolve_ui_dispatch_root_path()
        if not _bundle_writable(bundle_root):
            raise HTTPException(403, f"UI dispatch bundle is not writable: {bundle_root}")
        _write_ui_bundle(body)
        return read_dispatch_settings("ui")

    path = resolve_dispatch_settings_path(resolved_mode, create_ui=False)
    if not path.exists():
        raise HTTPException(404, f"Dispatch config not found: {path}")
    if not os.access(path, os.W_OK):
        raise HTTPException(403, f"Dispatch config is not writable: {path}")

    raw = _load_raw_config(path)
    _validate_raw_dispatch_config(raw, path)
    raw["runtime"] = body.runtime.model_dump()
    raw["tasks"] = body.tasks.model_dump()
    raw["workers"] = _merge_workers(raw.get("workers") or [], body.workers, body.providers, [], [])
    _validate_raw_dispatch_config(raw, path)

    serialized = yaml.safe_dump(raw, sort_keys=False, allow_unicode=False)
    path.write_text(serialized, encoding="utf-8")
    return read_dispatch_settings(resolved_mode)


def discover_skills(mode: DispatchSettingsMode | None = None) -> list[DiscoveredSkill]:
    resolved_mode = resolve_dispatch_settings_mode(mode)
    settings = read_dispatch_settings(resolved_mode)
    registered_ids = {skill.id for skill in settings.skills}
    discovered: dict[str, DiscoveredSkill] = {}
    _ensure_registry_layout()
    for root in resolve_skill_scan_roots():
        if not root.exists():
            continue
        for skill_dir in _iter_skill_dirs(root):
            skill = _build_discovered_skill(skill_dir, registered_ids)
            if skill is None:
                continue
            current = discovered.get(skill.id)
            if current is None or _discovered_skill_priority(skill) < _discovered_skill_priority(current):
                discovered[skill.id] = skill
    return sorted(discovered.values(), key=lambda item: (item.already_registered, item.name.lower(), item.path.lower()))


def import_skill_zip(body: SkillZipImportRequest) -> SkillZipImportResponse:
    resolved_mode = resolve_dispatch_settings_mode(body.mode)
    if resolved_mode == "ui":
        ensure_ui_dispatch_bundle(create=True)
        _sync_repo_skills_to_registry()

    filename = body.filename.strip()
    if not filename.lower().endswith(".zip"):
        raise HTTPException(400, "Only .zip skill bundles are supported")

    try:
        payload = base64.b64decode(body.content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(400, f"Invalid zip payload: {exc}") from exc

    if not payload:
        raise HTTPException(400, "Zip payload is empty")
    if len(payload) > 25 * 1024 * 1024:
        raise HTTPException(413, "Zip payload is too large")

    registry_root = resolve_registry_skills_root_path()
    _ensure_registry_layout()

    with tempfile.TemporaryDirectory(prefix="cairn-skill-import-") as temp_dir:
        temp_zip = Path(temp_dir) / filename
        temp_zip.write_bytes(payload)
        extract_root = Path(temp_dir) / "unzipped"
        extract_root.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(temp_zip) as archive:
                members = archive.infolist()
                if not members:
                    raise HTTPException(400, "Zip archive is empty")
                _validate_skill_zip_members(members)
                archive.extractall(extract_root)
        except HTTPException:
            raise
        except zipfile.BadZipFile as exc:
            raise HTTPException(400, f"Invalid zip archive: {exc}") from exc

        skill_dir = _find_imported_skill_dir(extract_root)
        if skill_dir is None:
            raise HTTPException(400, "Zip does not contain a valid SKILL.md skill directory")

        skill_file = skill_dir / "SKILL.md"
        try:
            text = skill_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            raise HTTPException(400, f"Unable to read imported SKILL.md: {exc}") from exc

        skill_name = _extract_skill_name(skill_dir, text)
        skill_id = _resolve_skill_id(
            skill_dir,
            name=skill_name,
            fallback=Path(filename).stem,
        )
        target_dir = registry_root / skill_id
        _sync_skill_dir(skill_dir, target_dir)
        _cleanup_legacy_imported_skill_dirs(
            registry_root,
            target_dir,
            skill_name=skill_name,
            skill_text=text,
        )
        if resolved_mode == "ui":
            _rewrite_ui_bundle_skill_aliases(
                old_skill_name=skill_name,
                new_skill_id=skill_id,
                new_skill_path=str(target_dir),
            )

    discovered = discover_skills(body.mode)
    return SkillZipImportResponse(
        imported_dir=str(target_dir),
        discovered=discovered,
    )


def run_worker_healthcheck(body: WorkerHealthcheckRequest) -> WorkerHealthcheckResponse:
    settings = read_dispatch_settings(body.mode)
    runtime = body.runtime or settings.runtime
    path = resolve_dispatch_settings_path(body.mode, create_ui=body.mode == "ui")
    existing_workers: list[dict[str, Any]] = []
    if path.exists():
        raw = _load_raw_config(path)
        existing_workers = raw.get("workers") or []
    merged_workers = _merge_workers(
        existing_workers=existing_workers,
        edited_workers=[body.worker],
        providers=body.providers,
        mcp_servers=body.mcp_servers,
        worker_bindings=body.worker_bindings,
        skills=body.skills,
    )
    temp_runtime_root = Path(tempfile.mkdtemp(prefix="cairn-healthcheck-"))
    try:
        temp_config = DispatchConfig.model_validate(
            {
                "server": "http://127.0.0.1:8000",
                "runtime": {
                    "interval": runtime.interval,
                    "max_workers": 1,
                    "max_running_projects": 1,
                    "max_project_workers": 1,
                    "healthcheck_timeout": runtime.healthcheck_timeout,
                    "prompt_group": runtime.prompt_group,
                },
                "tasks": {
                    "bootstrap": {
                        "timeout": settings.tasks.bootstrap.timeout,
                        "conclude_timeout": settings.tasks.bootstrap.conclude_timeout,
                    },
                    "reason": {
                        "timeout": settings.tasks.reason.timeout,
                        "max_intents": settings.tasks.reason.max_intents,
                        "allow_unavailable_dispatch": settings.tasks.reason.allow_unavailable_dispatch,
                        "unavailable_fact_limit": settings.tasks.reason.unavailable_fact_limit,
                    },
                    "explore": {
                        "timeout": settings.tasks.explore.timeout,
                        "conclude_timeout": settings.tasks.explore.conclude_timeout,
                    },
                },
                "execution": {
                    "backend": "local",
                    "work_dir": temp_runtime_root,
                },
                "workers": merged_workers,
            }
        )
    except Exception as exc:
        raise HTTPException(400, f"Invalid worker healthcheck config: {exc}") from exc
    worker_config = temp_config.workers[0]
    driver = get_driver(worker_config.type)
    runtime_manager = create_runtime_manager(temp_config)
    workspace_name = runtime_manager.ensure_startup_workspace()
    result = run_healthcheck(
        runtime_manager,
        workspace_name,
        worker_config,
        driver.build_startup_healthcheck(worker_config),
        timeout_seconds=runtime.healthcheck_timeout,
    )
    try:
        return _to_worker_healthcheck_result(worker_config.name, worker_config.type, driver.describe_startup_healthcheck(worker_config), result)
    finally:
        runtime_manager.close()
        shutil.rmtree(temp_runtime_root, ignore_errors=True)


def _to_worker_healthcheck_result(
    worker_name: str,
    worker_type: WorkerType,
    command: str,
    result: Any,
) -> WorkerHealthcheckResponse:
    stdout = result.result.stdout if hasattr(result, "result") else ""
    stderr = result.result.stderr if hasattr(result, "result") else ""
    returncode = result.result.returncode if hasattr(result, "result") else 1
    duration_ms = result.duration_ms if hasattr(result, "duration_ms") else 0
    http_status, response_preview = _parse_healthcheck_stdout(stdout)
    return WorkerHealthcheckResponse(
        ok=returncode == 0,
        worker_name=worker_name,
        worker_type=worker_type,
        returncode=returncode,
        duration_ms=duration_ms,
        http_status=http_status,
        response_preview=response_preview,
        stderr_preview=_preview_healthcheck_text(stderr),
        command=command,
    )


def _parse_healthcheck_stdout(stdout: str) -> tuple[str | None, str]:
    lines = stdout.splitlines()
    http_status: str | None = None
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if http_status is None and stripped.startswith("http_status="):
            http_status = stripped.partition("=")[2] or None
            continue
        body_lines.append(line)
    return http_status, _preview_healthcheck_text("\n".join(body_lines))


def _preview_healthcheck_text(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def ensure_ui_dispatch_bundle(*, create: bool) -> None:
    root = resolve_ui_dispatch_root_path()
    compiled_path = resolve_ui_dispatch_config_path()
    if root.exists() and compiled_path.exists():
        _ensure_registry_layout()
        return
    if not create:
        return
    source_path = resolve_dispatch_config_path()
    if not source_path.exists():
        raise HTTPException(404, f"Dispatch config not found: {source_path}")
    raw = _load_raw_config(source_path)
    _validate_raw_dispatch_config(raw, source_path)
    root.mkdir(parents=True, exist_ok=True)
    _ensure_registry_layout()
    providers = _providers_from_file_workers(raw.get("workers") or [])
    workers = [_worker_to_settings(worker, [], providers) for worker in raw.get("workers") or []]
    tasks = _tasks_to_settings(raw.get("tasks") or {})
    runtime = DispatchRuntimeSettings(**(raw.get("runtime") or {}))
    request = UpdateDispatchSettingsRequest(
        mode="ui",
        runtime=runtime,
        tasks=tasks,
        workers=workers,
        providers=providers,
        mcp_servers=[],
        skills=[],
        worker_bindings=[],
    )
    _write_ui_bundle(request)


def _write_ui_bundle(body: UpdateDispatchSettingsRequest) -> None:
    root = resolve_ui_dispatch_root_path()
    root.mkdir(parents=True, exist_ok=True)
    _ensure_registry_layout()
    compiled_path = resolve_ui_dispatch_config_path()
    existing_workers_raw = _read_json(root / _WORKERS_FILENAME, default=[])
    existing_providers_raw = _read_json(root / _PROVIDERS_FILENAME, default=[])
    existing_worker_tokens = {
        str(item.get("name", "")).strip(): str(item.get("auth_token", ""))
        for item in existing_workers_raw
        if str(item.get("name", "")).strip()
    }
    existing_provider_tokens = {
        str(item.get("id", "")).strip(): str(item.get("auth_token", ""))
        for item in existing_providers_raw
        if str(item.get("id", "")).strip()
    }

    normalized_workers = [
        DispatchWorkerSettings.model_validate(
            {
                **worker.model_dump(),
                "auth_token": worker.auth_token or (
                    existing_worker_tokens.get(worker.name, "")
                    if worker.has_auth_token
                    else ""
                ),
            }
        )
        for worker in body.workers
    ]
    normalized_providers = [
        ProviderSettings.model_validate(
            {
                **provider.model_dump(),
                "auth_token": provider.auth_token or (
                    existing_provider_tokens.get(provider.id, "")
                    if provider.has_auth_token
                    else ""
                ),
            }
        )
        for provider in body.providers
    ]

    settings_payload = {
        "mode": "ui",
        "hot_reload": True,
        "compiled_path": str(compiled_path),
        "source_path": str(root),
    }
    workers_payload = [
        _worker_to_bundle(worker, existing_auth_token=existing_worker_tokens.get(worker.name, ""))
        for worker in normalized_workers
    ]
    providers_payload = [
        _provider_to_bundle(provider, existing_auth_token=existing_provider_tokens.get(provider.id, ""))
        for provider in normalized_providers
    ]
    mcp_payload = [server.model_dump() for server in body.mcp_servers]
    skills_payload = [skill.model_dump() for skill in body.skills]
    bindings_payload = [binding.model_dump() for binding in body.worker_bindings]

    _write_json(root / _SETTINGS_FILENAME, settings_payload)
    _write_json(root / _WORKERS_FILENAME, workers_payload)
    _write_json(root / _PROVIDERS_FILENAME, providers_payload)
    _write_json(root / _MCP_SERVERS_FILENAME, mcp_payload)
    _write_json(root / _SKILLS_FILENAME, skills_payload)
    _write_json(root / _WORKER_BINDINGS_FILENAME, bindings_payload)

    raw = _compile_ui_bundle(
        body.runtime,
        body.tasks,
        normalized_workers,
        normalized_providers,
        body.mcp_servers,
        body.skills,
        body.worker_bindings,
    )
    _validate_raw_dispatch_config(raw, compiled_path)
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=False), encoding="utf-8")
    _write_validation_error("")


def _compile_ui_bundle(
    runtime: DispatchRuntimeSettings,
    tasks: DispatchTaskSettings,
    workers: list[DispatchWorkerSettings],
    providers: list[ProviderSettings],
    mcp_servers: list[McpServerSettings],
    skills: list[SkillSettings],
    worker_bindings: list[WorkerBindingSettings],
) -> dict[str, Any]:
    source_path = resolve_dispatch_config_path()
    source_raw = _load_raw_config(source_path) if source_path.exists() else {}
    result = deepcopy(source_raw)
    result.setdefault("server", source_raw.get("server", "http://127.0.0.1:8000"))
    result.setdefault("execution", source_raw.get("execution", {"backend": "local", "work_dir": ".cairn-runtime"}))
    if "container" in source_raw:
        result["container"] = deepcopy(source_raw["container"])
    if "common_env" in source_raw:
        result["common_env"] = deepcopy(source_raw["common_env"])
    result["runtime"] = runtime.model_dump()
    result["tasks"] = tasks.model_dump()
    result["workers"] = _merge_workers(source_raw.get("workers") or [], workers, providers, mcp_servers, worker_bindings, skills)
    return result


def _read_ui_bundle() -> dict[str, Any]:
    root = resolve_ui_dispatch_root_path()
    settings_raw = _read_json(root / _SETTINGS_FILENAME, default={})
    workers_raw = _read_json(root / _WORKERS_FILENAME, default=[])
    providers_raw = _read_json(root / _PROVIDERS_FILENAME, default=[])
    mcp_raw = _read_json(root / _MCP_SERVERS_FILENAME, default=[])
    skills_raw = _read_json(root / _SKILLS_FILENAME, default=[])
    bindings_raw = _read_json(root / _WORKER_BINDINGS_FILENAME, default=[])

    return {
        "settings": settings_raw,
        "workers": [DispatchWorkerSettings.model_validate(item) for item in workers_raw],
        "providers": [ProviderSettings.model_validate(item) for item in providers_raw],
        "mcp_servers": [McpServerSettings.model_validate(item) for item in mcp_raw],
        "skills": [SkillSettings.model_validate(item) for item in skills_raw],
        "worker_bindings": [WorkerBindingSettings.model_validate(item) for item in bindings_raw],
    }


def _rewrite_ui_bundle_skill_aliases(*, old_skill_name: str, new_skill_id: str, new_skill_path: str) -> None:
    root = resolve_ui_dispatch_root_path()
    skills_raw = _read_json(root / _SKILLS_FILENAME, default=[])
    changed = False
    updated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in skills_raw:
        if not isinstance(item, dict):
            continue
        payload = dict(item)
        item_name = str(payload.get("name", "")).strip()
        item_id = str(payload.get("id", "")).strip()
        item_path = str(payload.get("path", "")).strip()
        if item_name == old_skill_name and (item_id != new_skill_id or item_path != new_skill_path):
            payload["id"] = new_skill_id
            payload["path"] = new_skill_path
            changed = True
        final_id = str(payload.get("id", "")).strip()
        if final_id and final_id in seen_ids:
            changed = True
            continue
        if final_id:
            seen_ids.add(final_id)
        updated.append(payload)

    if changed:
        _write_json(root / _SKILLS_FILENAME, updated)


def _cleanup_legacy_imported_skill_dirs(
    registry_root: Path,
    target_dir: Path,
    *,
    skill_name: str,
    skill_text: str,
) -> None:
    target_resolved = target_dir.resolve()
    for candidate in registry_root.iterdir():
        if not candidate.is_dir():
            continue
        try:
            if candidate.resolve() == target_resolved:
                continue
        except OSError:
            continue
        skill_md = candidate / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            candidate_text = skill_md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        candidate_name = _extract_skill_name(candidate, candidate_text)
        if candidate_name != skill_name:
            continue
        if candidate_text != skill_text:
            continue
        shutil.rmtree(candidate, ignore_errors=True)


def _tasks_to_settings(tasks_raw: dict[str, Any]) -> DispatchTaskSettings:
    return DispatchTaskSettings(
        bootstrap=DispatchBootstrapTaskSettings(**(tasks_raw.get("bootstrap") or {})),
        reason=DispatchReasonTaskSettings(**(tasks_raw.get("reason") or {})),
        explore=DispatchExploreTaskSettings(**(tasks_raw.get("explore") or {})),
    )


def _load_raw_config(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"Failed to parse dispatch config: {exc}") from exc
    if not isinstance(raw, dict):
        raise HTTPException(400, "Dispatch config root must be a YAML object")
    return raw


def _validate_raw_dispatch_config(raw: dict[str, Any], path: Path) -> None:
    try:
        DispatchConfig.model_validate(raw)
    except Exception as exc:
        _write_validation_error(str(exc))
        raise HTTPException(400, f"Invalid dispatch config {path}: {exc}") from exc


def _worker_to_settings(
    worker_raw: dict[str, Any],
    worker_bindings: list[WorkerBindingSettings],
    providers: list[ProviderSettings],
) -> DispatchWorkerSettings:
    worker_type = worker_raw["type"]
    env = deepcopy(worker_raw.get("env") or {})
    field_map = _WORKER_ENV_FIELD_MAP[worker_type]
    known_env_keys = {value for value in field_map.values() if value}
    known_env_keys.update({_MCP_ENV_KEY, _SKILL_ENV_KEY, _PROVIDER_ENV_KEY})
    context_window = None
    if field_map.get("context_window"):
        raw_context = env.get(field_map["context_window"], "")
        if str(raw_context).strip():
            context_window = int(str(raw_context).strip())
    binding = next(
        (item for item in worker_bindings if item.worker_name == str(worker_raw.get("name", "")).strip()),
        None,
    )
    provider_id = _infer_provider_id(worker_raw)
    provider = next((item for item in providers if item.id == provider_id), None)
    settings = DispatchWorkerSettings(
        source_name=str(worker_raw.get("name", "")).strip(),
        name=str(worker_raw.get("name", "")).strip(),
        enabled=bool(worker_raw.get("enabled", True)),
        type=worker_type,
        task_types=_normalize_task_types(worker_raw.get("task_types") or []),
        max_running=worker_raw["max_running"],
        priority=worker_raw["priority"],
        provider_id=provider_id,
        provider_supported=_PROVIDER_SUPPORT_MATRIX[worker_type],
        model=provider.model if provider else str(env.get(field_map.get("model", ""), "")).strip(),
        base_url=provider.base_url if provider else str(env.get(field_map.get("base_url", ""), "")).strip(),
        auth_token="",
        has_auth_token=provider.has_auth_token if provider else bool(str(env.get(field_map.get("auth_token", ""), "")).strip()),
        provider_api=provider.provider_api if provider else str(env.get(field_map.get("provider_api", ""), "")).strip(),
        context_window=provider.context_window if provider and provider.context_window is not None else context_window,
        extra_env={
            str(key): str(value)
            for key, value in env.items()
            if str(key) not in known_env_keys
        },
        mcp_server_ids=list(binding.mcp_server_ids) if binding else [],
        skill_ids=list(binding.skill_ids) if binding else [],
        mcp_supported=_MCP_SUPPORT_MATRIX[worker_type],
        skill_supported=_SKILL_SUPPORT_MATRIX[worker_type],
    )
    return settings


def _worker_to_bundle(worker: DispatchWorkerSettings, *, existing_auth_token: str = "") -> dict[str, Any]:
    payload = worker.model_dump()
    if not payload.get("auth_token") and payload.get("has_auth_token") and existing_auth_token:
        payload["auth_token"] = existing_auth_token
    payload["extra_env"] = _filter_editable_extra_env(worker.extra_env)
    return payload


def _provider_to_bundle(provider: ProviderSettings, *, existing_auth_token: str = "") -> dict[str, Any]:
    payload = provider.model_dump()
    if not payload.get("auth_token") and payload.get("has_auth_token") and existing_auth_token:
        payload["auth_token"] = existing_auth_token
    payload["extra_env"] = _filter_editable_extra_env(provider.extra_env)
    return payload


def _filter_editable_extra_env(env: dict[str, Any]) -> dict[str, str]:
    internal_keys = {_MCP_ENV_KEY, _SKILL_ENV_KEY, _PROVIDER_ENV_KEY}
    return {
        str(key): str(value)
        for key, value in (env or {}).items()
        if str(key) and str(key) not in internal_keys
    }


def _normalize_task_types(task_types: list[Any]) -> list[TaskType]:
    seen = {str(item).strip() for item in task_types}
    return [task_type for task_type in _TASK_TYPE_ORDER if task_type in seen]


def _merge_workers(
    existing_workers: list[dict[str, Any]],
    edited_workers: list[DispatchWorkerSettings],
    providers: list[ProviderSettings],
    mcp_servers: list[McpServerSettings],
    worker_bindings: list[WorkerBindingSettings],
    skills: list[SkillSettings] | None = None,
) -> list[dict[str, Any]]:
    existing_by_name = {}
    for worker in existing_workers:
        name = str(worker.get("name", "")).strip()
        if name:
            existing_by_name[name] = deepcopy(worker)

    mcp_by_id = {server.id: server for server in mcp_servers if server.enabled}
    binding_by_worker = {binding.worker_name: binding for binding in worker_bindings}
    provider_by_id = {provider.id: provider for provider in providers}
    result: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for worker in edited_workers:
        if worker.name in used_names:
            raise HTTPException(400, f"Duplicate worker name: {worker.name}")
        used_names.add(worker.name)

        source_name = worker.source_name or worker.name
        base = existing_by_name.get(source_name, {"env": {}})
        existing_env = deepcopy(base.get("env") or {})
        env = {
            str(key): value
            for key, value in existing_env.items()
            if str(key) not in {_MCP_ENV_KEY, _SKILL_ENV_KEY, _PROVIDER_ENV_KEY}
        }
        _clear_known_worker_env(env)
        field_map = _WORKER_ENV_FIELD_MAP[worker.type]
        provider = provider_by_id.get(worker.provider_id) if worker.provider_id else None
        model_value = provider.model if provider else worker.model
        base_url_value = provider.base_url if provider else worker.base_url
        auth_token_value = provider.auth_token if provider and provider.auth_token else worker.auth_token
        provider_api_value = provider.provider_api if provider else worker.provider_api
        context_window_value = provider.context_window if provider and provider.context_window is not None else worker.context_window
        extra_env_value = provider.extra_env if provider else worker.extra_env

        _set_env_value(env, field_map.get("model"), model_value)
        _set_env_value(env, field_map.get("base_url"), base_url_value)
        _merge_auth_token(
            env,
            field_map.get("auth_token"),
            auth_token_value,
            preserve_existing=worker.has_auth_token,
            existing_env=existing_env,
        )
        _set_env_value(env, field_map.get("provider_api"), provider_api_value)
        _set_context_window(env, field_map.get("context_window"), context_window_value)
        env.update(
            {
                key: value
                for key, value in extra_env_value.items()
                if key and key not in {_MCP_ENV_KEY, _SKILL_ENV_KEY, _PROVIDER_ENV_KEY}
            }
        )
        if worker.type != "mock":
            env[_PROVIDER_ENV_KEY] = json.dumps(
                _serialize_provider_spec(worker, provider),
                ensure_ascii=True,
                separators=(",", ":"),
            )

        binding = binding_by_worker.get(worker.name)
        if binding and _MCP_SUPPORT_MATRIX[worker.type]:
            enabled_servers = []
            for server_id in binding.mcp_server_ids:
                server = mcp_by_id.get(server_id)
                if server is not None:
                    enabled_servers.append(_serialize_mcp_server(server))
            if enabled_servers:
                env[_MCP_ENV_KEY] = json.dumps(enabled_servers, ensure_ascii=True, separators=(",", ":"))
            else:
                env.pop(_MCP_ENV_KEY, None)
        else:
            env.pop(_MCP_ENV_KEY, None)

        if _SKILL_SUPPORT_MATRIX[worker.type]:
            bound_skill_ids = set(binding.skill_ids) if binding else set()
            enabled_skills = [
                _serialize_skill_spec(item)
                for item in skills or []
                if item.enabled
                and (item.id in bound_skill_ids or _skill_enabled_for_worker(item, worker.type))
                and _skill_enabled_for_worker(item, worker.type)
            ]
            if enabled_skills:
                env[_SKILL_ENV_KEY] = json.dumps(enabled_skills, ensure_ascii=True, separators=(",", ":"))
            else:
                env.pop(_SKILL_ENV_KEY, None)
        else:
            env.pop(_SKILL_ENV_KEY, None)

        merged = deepcopy(base)
        merged.pop("provider_id", None)
        merged.update(
            {
                "name": worker.name,
                "enabled": worker.enabled,
                "type": worker.type,
                "task_types": worker.task_types,
                "max_running": worker.max_running,
                "priority": worker.priority,
                "env": env,
            }
        )
        result.append(merged)

    return result


def _serialize_mcp_server(server: McpServerSettings) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": server.id,
        "name": server.name,
        "transport": server.transport,
        "env": server.env,
    }
    if server.transport == "stdio":
        payload["command"] = server.command
        payload["args"] = server.args
    else:
        payload["url"] = server.url
    return payload


def _clear_known_worker_env(env: dict[str, Any]) -> None:
    known_keys = {
        key
        for field_map in _WORKER_ENV_FIELD_MAP.values()
        for key in field_map.values()
        if key
    }
    known_keys.update({_MCP_ENV_KEY, _SKILL_ENV_KEY, _PROVIDER_ENV_KEY})
    for key in known_keys:
        env.pop(key, None)


def _serialize_provider_spec(worker: DispatchWorkerSettings, provider: ProviderSettings | None) -> dict[str, Any]:
    if provider is not None:
        return {
            "id": provider.id,
            "name": provider.name,
            "kind": provider.kind,
            "model": provider.model,
            "base_url": provider.base_url,
            "provider_api": provider.provider_api,
            "context_window": provider.context_window,
            "extra_env": provider.extra_env,
        }
    return {
        "id": worker.provider_id or "",
        "name": worker.name,
        "kind": worker.type,
        "model": worker.model,
        "base_url": worker.base_url,
        "provider_api": worker.provider_api,
        "context_window": worker.context_window,
        "extra_env": worker.extra_env,
    }


def _serialize_skill_spec(skill: SkillSettings) -> dict[str, Any]:
    return {
        "id": skill.id,
        "name": skill.name,
        "path": skill.path,
        "description": skill.description,
        "enabled_claude": skill.enabled_claude,
        "enabled_codex": skill.enabled_codex,
    }


def _skill_enabled_for_worker(skill: SkillSettings, worker_type: WorkerType) -> bool:
    if worker_type == "claudecode":
        return skill.enabled_claude
    if worker_type == "codex":
        return skill.enabled_codex
    return False


def _iter_skill_dirs(root: Path) -> list[Path]:
    matches: list[Path] = []
    for path in root.rglob("SKILL.md"):
        parent = path.parent
        if parent.name.startswith(".") and parent.name not in {".codex", ".claude"}:
            continue
        matches.append(parent)
    return matches


def _build_discovered_skill(skill_dir: Path, registered_ids: set[str]) -> DiscoveredSkill | None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None
    try:
        text = skill_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    name = _extract_skill_name(skill_dir, text)
    description = _extract_skill_description(text)
    skill_id = _resolve_skill_id(skill_dir, name=name)
    return DiscoveredSkill(
        id=skill_id,
        name=name,
        path=str(skill_dir),
        description=description,
        source=_classify_skill_source(skill_dir),
        already_registered=skill_id in registered_ids,
    )


def _extract_skill_name(skill_dir: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            value = stripped.lstrip("#").strip()
            if value:
                return value
    return skill_dir.name


def _extract_skill_description(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped[:240]
    return ""


def _resolve_skill_id(skill_dir: Path, *, name: str = "", fallback: str = "") -> str:
    for candidate in (name, skill_dir.name, fallback):
        skill_id = _slugify_skill_id(candidate)
        if skill_id != "skill":
            return skill_id
    return "skill"


def _slugify_skill_id(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return text or "skill"


def _classify_skill_source(path: Path) -> str:
    text = str(path)
    registry_root = str(resolve_registry_root_path())
    if registry_root and registry_root in text:
        return "registry"
    if "datas/cairn-runtime/skills" in text:
        return "runtime"
    if text.endswith("/skills") or "/skills/" in text:
        return "project"
    return "container"


def _discovered_skill_priority(skill: DiscoveredSkill) -> int:
    order = {
        "registry": 0,
        "runtime": 1,
        "project": 2,
        "container": 3,
    }
    return order.get(skill.source, 99)


def _ensure_registry_layout() -> None:
    resolve_registry_skills_root_path().mkdir(parents=True, exist_ok=True)
    resolve_registry_mcp_root_path().mkdir(parents=True, exist_ok=True)


def _sync_repo_skills_to_registry() -> None:
    registry_root = resolve_registry_skills_root_path()
    _ensure_registry_layout()
    synced_ids: set[str] = set()
    for repo_root in resolve_repo_skill_roots():
        if not repo_root.exists():
            continue
        for skill_dir in _iter_skill_dirs(repo_root):
            skill_id = _slugify_skill_id(skill_dir.name)
            if skill_id in synced_ids:
                continue
            target_dir = registry_root / skill_id
            if _sync_skill_dir(skill_dir, target_dir):
                synced_ids.add(skill_id)
                skill_file = target_dir / "SKILL.md"
                if not skill_file.exists() and (skill_dir / "SKILL.md").exists():
                    shutil.copy2(skill_dir / "SKILL.md", skill_file)


def _sync_skill_dir(source_dir: Path, target_dir: Path) -> bool:
    if not source_dir.exists():
        return False
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    return True


def _validate_skill_zip_members(members: list[zipfile.ZipInfo]) -> None:
    total_size = 0
    for member in members:
        name = member.filename
        if not name or name.endswith("/"):
            continue
        normalized = Path(name)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise HTTPException(400, f"Unsafe zip path: {name}")
        total_size += max(member.file_size, 0)
        if total_size > 50 * 1024 * 1024:
            raise HTTPException(413, "Unzipped skill bundle is too large")


def _find_imported_skill_dir(root: Path) -> Path | None:
    direct_skill = root / "SKILL.md"
    if direct_skill.exists():
        return root
    matches = _iter_skill_dirs(root)
    if not matches:
        return None
    matches.sort(key=lambda item: (len(item.parts), str(item).lower()))
    return matches[0]


def _providers_from_file_workers(workers_raw: list[dict[str, Any]]) -> list[ProviderSettings]:
    providers: list[ProviderSettings] = []
    for worker_raw in workers_raw:
        worker_type = worker_raw.get("type")
        if worker_type not in _WORKER_ENV_FIELD_MAP or worker_type == "mock":
            continue
        env = deepcopy(worker_raw.get("env") or {})
        field_map = _WORKER_ENV_FIELD_MAP[worker_type]
        known_env_keys = {value for value in field_map.values() if value}
        known_env_keys.update({_MCP_ENV_KEY, _SKILL_ENV_KEY, _PROVIDER_ENV_KEY})
        provider_id = _infer_provider_id(worker_raw)
        providers.append(
            ProviderSettings(
                id=provider_id,
                name=f"{worker_raw.get('name', provider_id)} Provider",
                enabled=True,
                kind=worker_type,
                model=str(env.get(field_map.get("model", ""), "")).strip(),
                base_url=str(env.get(field_map.get("base_url", ""), "")).strip(),
                auth_token="",
                has_auth_token=bool(str(env.get(field_map.get("auth_token", ""), "")).strip()),
                provider_api=str(env.get(field_map.get("provider_api", ""), "")).strip(),
                context_window=(
                    int(str(env.get(field_map["context_window"], "")).strip())
                    if field_map.get("context_window") and str(env.get(field_map["context_window"], "")).strip()
                    else None
                ),
                extra_env={
                    str(key): str(value)
                    for key, value in env.items()
                    if str(key) not in known_env_keys
                },
            )
        )
    deduped: dict[str, ProviderSettings] = {}
    for provider in providers:
        deduped[provider.id] = provider
    return list(deduped.values())


def _infer_provider_id(worker_raw: dict[str, Any]) -> str:
    explicit = str(worker_raw.get("provider_id", "")).strip()
    if explicit:
        return explicit
    worker_name = str(worker_raw.get("name", "")).strip() or "worker"
    return f"{worker_name}_provider"


def _set_env_value(env: dict[str, Any], key: str | None, value: str) -> None:
    if not key:
        return
    if value:
        env[key] = value
        return
    env.pop(key, None)


def _merge_auth_token(
    env: dict[str, Any],
    key: str | None,
    value: str,
    *,
    preserve_existing: bool = False,
    existing_env: dict[str, Any] | None = None,
) -> None:
    if not key:
        return
    if value:
        env[key] = value
        return
    if preserve_existing and existing_env is not None:
        existing = str(existing_env.get(key, "")).strip()
        if existing:
            env[key] = existing
            return
    existing = str(env.get(key, "")).strip()
    if not existing:
        env.pop(key, None)


def _set_context_window(env: dict[str, Any], key: str | None, value: int | None) -> None:
    if not key:
        return
    if value is None:
        env.pop(key, None)
        return
    env[key] = str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Failed to parse UI dispatch bundle file {path}: {exc}") from exc


def _write_validation_error(message: str) -> None:
    root = resolve_ui_dispatch_root_path()
    if not root.exists():
        return
    (root / _VALIDATION_ERROR_FILENAME).write_text(message.strip(), encoding="utf-8")


def _read_validation_error() -> str:
    path = resolve_ui_dispatch_root_path() / _VALIDATION_ERROR_FILENAME
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _bundle_writable(root: Path) -> bool:
    if not root.exists():
        return os.access(root.parent, os.W_OK)
    return os.access(root, os.W_OK)


def _isoformat(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
