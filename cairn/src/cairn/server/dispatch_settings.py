from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException

from cairn.dispatcher.config import DispatchConfig, TaskType, WorkerType
from cairn.server.db import DEFAULT_DB
from cairn.server.models import (
    DispatchSettingsMode,
    DispatchRuntimeSettings,
    DispatchSettings,
    DispatchWorkerSettings,
    UpdateDispatchSettingsRequest,
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

_TASK_TYPE_ORDER: tuple[TaskType, ...] = ("bootstrap", "reason", "explore")
_DISPATCH_SETTINGS_MODE_ENV = "CAIRN_DISPATCH_SETTINGS_MODE"
_UI_DISPATCH_CONFIG_ENV = "CAIRN_UI_DISPATCH_CONFIG"


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
        return cwd_datas / "dispatch_ui.yaml"
    return DEFAULT_DB.parent / "dispatch_ui.yaml"


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

    path = resolve_ui_dispatch_config_path()
    if create_ui and not path.exists():
        source_path = resolve_dispatch_config_path()
        if not source_path.exists():
            raise HTTPException(404, f"Dispatch config not found: {source_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def read_dispatch_settings(mode: DispatchSettingsMode | None = None) -> DispatchSettings:
    resolved_mode = resolve_dispatch_settings_mode(mode)
    path = resolve_dispatch_settings_path(resolved_mode, create_ui=resolved_mode == "ui")
    if not path.exists():
        raise HTTPException(404, f"Dispatch config not found: {path}")

    raw = _load_raw_config(path)
    _validate_raw_dispatch_config(raw, path)
    runtime_raw = raw.get("runtime") or {}
    workers_raw = raw.get("workers") or []

    return DispatchSettings(
        mode=resolved_mode,
        path=str(path),
        writable=os.access(path, os.W_OK),
        runtime=DispatchRuntimeSettings(**runtime_raw),
        workers=[_worker_to_settings(worker) for worker in workers_raw],
        restart_required=True,
    )


def write_dispatch_settings(body: UpdateDispatchSettingsRequest) -> DispatchSettings:
    resolved_mode = resolve_dispatch_settings_mode(body.mode)
    path = resolve_dispatch_settings_path(resolved_mode, create_ui=resolved_mode == "ui")
    if not path.exists():
        raise HTTPException(404, f"Dispatch config not found: {path}")
    if not os.access(path, os.W_OK):
        raise HTTPException(403, f"Dispatch config is not writable: {path}")

    raw = _load_raw_config(path)
    _validate_raw_dispatch_config(raw, path)

    raw["runtime"] = body.runtime.model_dump()
    raw["workers"] = _merge_workers(raw.get("workers") or [], body.workers)
    _validate_raw_dispatch_config(raw, path)

    serialized = yaml.safe_dump(raw, sort_keys=False, allow_unicode=False)
    path.write_text(serialized, encoding="utf-8")
    return read_dispatch_settings(resolved_mode)


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
        raise HTTPException(400, f"Invalid dispatch config {path}: {exc}") from exc


def _worker_to_settings(worker_raw: dict[str, Any]) -> DispatchWorkerSettings:
    worker_type = worker_raw["type"]
    env = deepcopy(worker_raw.get("env") or {})
    field_map = _WORKER_ENV_FIELD_MAP[worker_type]

    context_window = None
    if field_map.get("context_window"):
        raw_context = env.get(field_map["context_window"], "")
        if str(raw_context).strip():
            context_window = int(str(raw_context).strip())

    return DispatchWorkerSettings(
        source_name=str(worker_raw.get("name", "")).strip(),
        name=str(worker_raw.get("name", "")).strip(),
        type=worker_type,
        task_types=_normalize_task_types(worker_raw.get("task_types") or []),
        max_running=worker_raw["max_running"],
        priority=worker_raw["priority"],
        model=str(env.get(field_map.get("model", ""), "")).strip(),
        base_url=str(env.get(field_map.get("base_url", ""), "")).strip(),
        auth_token="",
        has_auth_token=bool(str(env.get(field_map.get("auth_token", ""), "")).strip()),
        provider_api=str(env.get(field_map.get("provider_api", ""), "")).strip(),
        context_window=context_window,
    )


def _normalize_task_types(task_types: list[Any]) -> list[TaskType]:
    seen = {str(item).strip() for item in task_types}
    return [task_type for task_type in _TASK_TYPE_ORDER if task_type in seen]


def _merge_workers(existing_workers: list[dict[str, Any]], edited_workers: list[DispatchWorkerSettings]) -> list[dict[str, Any]]:
    existing_by_name = {}
    for worker in existing_workers:
        name = str(worker.get("name", "")).strip()
        if name:
            existing_by_name[name] = deepcopy(worker)

    result: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for worker in edited_workers:
        if worker.name in used_names:
            raise HTTPException(400, f"Duplicate worker name: {worker.name}")
        used_names.add(worker.name)

        source_name = worker.source_name or worker.name
        base = existing_by_name.get(source_name, {"env": {}})
        env = deepcopy(base.get("env") or {})
        _clear_known_worker_env(env)
        field_map = _WORKER_ENV_FIELD_MAP[worker.type]

        _set_env_value(env, field_map.get("model"), worker.model)
        _set_env_value(env, field_map.get("base_url"), worker.base_url)
        _merge_auth_token(env, field_map.get("auth_token"), worker.auth_token)
        _set_env_value(env, field_map.get("provider_api"), worker.provider_api)
        _set_context_window(env, field_map.get("context_window"), worker.context_window)

        merged = deepcopy(base)
        merged.update(
            {
                "name": worker.name,
                "type": worker.type,
                "task_types": worker.task_types,
                "max_running": worker.max_running,
                "priority": worker.priority,
                "env": env,
            }
        )
        result.append(merged)

    return result


def _clear_known_worker_env(env: dict[str, Any]) -> None:
    known_keys = {
        key
        for field_map in _WORKER_ENV_FIELD_MAP.values()
        for key in field_map.values()
        if key
    }
    for key in known_keys:
        env.pop(key, None)


def _set_env_value(env: dict[str, Any], key: str | None, value: str) -> None:
    if not key:
        return
    if value:
        env[key] = value
        return
    env.pop(key, None)


def _merge_auth_token(env: dict[str, Any], key: str | None, value: str) -> None:
    if not key:
        return
    if value:
        env[key] = value
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
