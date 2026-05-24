from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from pathlib import PurePath
from typing import Callable

from cairn.dispatcher.config import WorkerConfig
from cairn.dispatcher.protocol.client import CairnClient
from cairn.dispatcher.runtime.cancellation import TaskCancellation
from cairn.dispatcher.runtime.heartbeat import HeartbeatLease
from cairn.dispatcher.runtime.manager import RuntimeManager
from cairn.dispatcher.runtime.process import ProcessResult
from cairn.dispatcher.workers.runtime_injection import prepare_worker_runtime_files

LOG_PREVIEW_LIMIT = 1200
GRAPH_SNAPSHOT_ROOT = "prompts"
OBSERVER_RUN_ROOT = "runs"
LOG = logging.getLogger(__name__)
AGENT_SESSION_PREFIXES = {
    "codex": "codex",
    "claudecode": "claude",
    "claude": "claude",
    "pi": "pi",
}


@dataclass(slots=True)
class HealthcheckRun:
    result: ProcessResult
    duration_ms: int


@dataclass(slots=True)
class ConcludeWriteResult:
    status: str
    fact_id: str | None = None


@dataclass(slots=True)
class WorkerRunRecord:
    run_id: str
    project_id: str
    intent_id: str | None
    phase: str
    worker_name: str
    agent_type: str
    workspace_name: str
    workspace_path: str
    session_id: str | None
    status: str
    started_at: str
    updated_at: str
    ended_at: str | None = None
    exit_code: int | None = None
    timed_out: bool = False
    cancelled: bool = False
    cancel_reason: str | None = None
    duration_ms: int | None = None
    skill_ids: list[str] | None = None
    skill_names: list[str] | None = None
    skill_source_paths: list[str] | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""


def preview(text: str, limit: int = LOG_PREVIEW_LIMIT) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_observer_session_id(agent_type: str, session_id: str | None) -> str | None:
    if session_id is None:
        return None
    value = session_id.strip()
    if not value:
        return None
    if ":" in value:
        return value
    prefix = AGENT_SESSION_PREFIXES.get(agent_type.strip().lower())
    if prefix is None:
        return value
    return f"{prefix}:{value}"


def start_worker_run_record(
    runtime_manager: RuntimeManager,
    *,
    project_id: str,
    intent_id: str | None,
    phase: str,
    worker: WorkerConfig,
    agent_type: str,
    workspace_name: str,
    session_id: str | None,
) -> WorkerRunRecord:
    started_at = now_utc_iso()
    skill_ids, skill_names, skill_source_paths = extract_worker_skills(worker)
    record = WorkerRunRecord(
        run_id=uuid.uuid4().hex,
        project_id=project_id,
        intent_id=intent_id,
        phase=phase,
        worker_name=worker.name,
        agent_type=agent_type,
        workspace_name=workspace_name,
        workspace_path=str(runtime_manager.workspace_path(workspace_name)),
        session_id=normalize_observer_session_id(agent_type, session_id),
        status="running",
        started_at=started_at,
        updated_at=started_at,
        skill_ids=skill_ids,
        skill_names=skill_names,
        skill_source_paths=skill_source_paths,
    )
    write_worker_run_record(runtime_manager, record)
    return record


def finish_worker_run_record(
    runtime_manager: RuntimeManager,
    record: WorkerRunRecord | None,
    result: ProcessResult,
    *,
    started: float,
    session_id: str | None = None,
) -> None:
    if record is None:
        return
    record.session_id = normalize_observer_session_id(record.agent_type, session_id) or record.session_id
    record.status = "cancelled" if result.cancelled else "timeout" if did_timeout(result) else "success" if result.returncode == 0 else "failed"
    record.updated_at = now_utc_iso()
    record.ended_at = record.updated_at
    record.exit_code = result.returncode
    record.timed_out = result.timed_out
    record.cancelled = result.cancelled
    record.cancel_reason = result.cancel_reason
    record.duration_ms = int((time.perf_counter() - started) * 1000)
    record.stdout_preview = preview(result.stdout)
    record.stderr_preview = preview(result.stderr)
    write_worker_run_record(runtime_manager, record)


def update_worker_run_record(
    runtime_manager: RuntimeManager,
    record: WorkerRunRecord | None,
    *,
    session_id: str | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
) -> None:
    if record is None:
        return
    changed = False
    normalized_session_id = normalize_observer_session_id(record.agent_type, session_id)
    if normalized_session_id and normalized_session_id != record.session_id:
        record.session_id = normalized_session_id
        changed = True
    if stdout is not None:
        stdout_preview = preview(stdout)
        if stdout_preview != record.stdout_preview:
            record.stdout_preview = stdout_preview
            changed = True
    if stderr is not None:
        stderr_preview = preview(stderr)
        if stderr_preview != record.stderr_preview:
            record.stderr_preview = stderr_preview
            changed = True
    if not changed:
        return
    record.updated_at = now_utc_iso()
    write_worker_run_record(runtime_manager, record)


def write_worker_run_record(runtime_manager: RuntimeManager, record: WorkerRunRecord) -> None:
    payload = {
        "schema_version": 1,
        "run_id": record.run_id,
        "project_id": record.project_id,
        "intent_id": record.intent_id,
        "phase": record.phase,
        "worker_name": record.worker_name,
        "agent_type": record.agent_type,
        "workspace_name": record.workspace_name,
        "workspace_path": record.workspace_path,
        "session_id": record.session_id,
        "status": record.status,
        "started_at": record.started_at,
        "updated_at": record.updated_at,
        "ended_at": record.ended_at,
        "exit_code": record.exit_code,
        "timed_out": record.timed_out,
        "cancelled": record.cancelled,
        "cancel_reason": record.cancel_reason,
        "duration_ms": record.duration_ms,
        "skill_ids": record.skill_ids or [],
        "skill_names": record.skill_names or [],
        "skill_source_paths": record.skill_source_paths or [],
        "stdout_preview": record.stdout_preview,
        "stderr_preview": record.stderr_preview,
    }
    path = PurePath(OBSERVER_RUN_ROOT) / record.project_id / f"{record.run_id}.json"
    runtime_manager.write_observer_text_file(str(path), json.dumps(payload, ensure_ascii=False, indent=2))


def mark_stale_worker_run_records(work_dir: Path) -> int:
    runs_root = work_dir.resolve() / "observer" / OBSERVER_RUN_ROOT
    if not runs_root.exists():
        return 0
    marked = 0
    stale_at = now_utc_iso()
    for path in runs_root.glob("*/*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            LOG.warning("skipping unreadable observer run record path=%s", path)
            continue
        if payload.get("status") != "running":
            continue
        payload["status"] = "stale"
        payload["updated_at"] = stale_at
        payload["ended_at"] = payload.get("ended_at") or stale_at
        payload["cancelled"] = True
        payload["cancel_reason"] = "dispatcher_restarted"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        marked += 1
    if marked:
        LOG.info("marked stale observer run records count=%s root=%s", marked, runs_root)
    return marked


def did_timeout(result: ProcessResult) -> bool:
    return not result.cancelled and (result.timed_out or result.returncode in (124, 137))


def extract_worker_skills(worker: WorkerConfig) -> tuple[list[str], list[str], list[str]]:
    raw = worker.env.get("CAIRN_SKILLS")
    if raw is None or not str(raw).strip():
        return [], [], []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [], [], []
    if not isinstance(payload, list):
        return [], [], []

    skill_ids: list[str] = []
    skill_names: list[str] = []
    skill_source_paths: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("id", "")).strip()
        skill_name = str(item.get("name", "")).strip()
        source_path = str(
            item.get("source_path") or item.get("original_path") or item.get("path") or ""
        ).strip()
        if skill_id:
            skill_ids.append(skill_id)
        if skill_name:
            skill_names.append(skill_name)
        elif skill_id:
            skill_names.append(skill_id)
        if source_path:
            skill_source_paths.append(source_path)
    return skill_ids, skill_names, skill_source_paths


def cancel_reason(result: ProcessResult, cancellation: TaskCancellation | None = None) -> str | None:
    if result.cancelled:
        return result.cancel_reason or "cancelled"
    if cancellation is not None:
        return cancellation.reason
    return None


def write_graph_snapshot_reference(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    graph_yaml: str,
    *,
    phase: str,
) -> str:
    relative_path = str(PurePath(GRAPH_SNAPSHOT_ROOT) / f"{phase}-{uuid.uuid4().hex[:12]}" / "graph.yaml")
    path = runtime_manager.write_text_file(workspace_name, relative_path, graph_yaml)
    return (
        "The graph YAML snapshot is stored in this file inside the current project workspace:\n\n"
        f"{path}\n\n"
        "Before using the graph, read the entire file and treat its contents as the YAML snapshot "
        "for this Graph section."
    )


def run_healthcheck(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
    command: list[str],
    *,
    timeout_seconds: int,
    lease: HeartbeatLease | None = None,
    cancellation: TaskCancellation | None = None,
) -> HealthcheckRun:
    env = dict(worker.env)
    env.update(prepare_worker_runtime_files(runtime_manager, workspace_name, worker))
    process = runtime_manager.build_exec_process(
        workspace_name,
        env,
        command,
        timeout_seconds=timeout_seconds,
    )
    process.start()
    if lease is not None:
        lease.attach_process(process)
    if cancellation is not None:
        cancellation.attach_process(process)
    started = time.perf_counter()
    try:
        result = process.communicate(timeout=timeout_seconds)
    finally:
        if lease is not None:
            lease.attach_process(None)
        if cancellation is not None:
            cancellation.attach_process(None)
    duration_ms = int((time.perf_counter() - started) * 1000)
    return HealthcheckRun(result=result, duration_ms=duration_ms)


def run_worker_process(
    runtime_manager: RuntimeManager,
    workspace_name: str,
    worker: WorkerConfig,
    argv: list[str],
    *,
    phase: str,
    timeout_seconds: int,
    lease: HeartbeatLease | None = None,
    cancellation: TaskCancellation | None = None,
    on_output: Callable[[str, str, str, str], None] | None = None,
) -> ProcessResult:
    LOG.info(
        "starting worker process workspace=%s worker=%s phase=%s timeout=%ss",
        workspace_name,
        worker.name,
        phase,
        timeout_seconds,
    )
    env = dict(worker.env)
    env.update(prepare_worker_runtime_files(runtime_manager, workspace_name, worker))
    process = runtime_manager.build_exec_process(
        workspace_name,
        env,
        argv,
        timeout_seconds=timeout_seconds,
    )
    process.start()
    if lease is not None:
        lease.attach_process(process)
    if cancellation is not None:
        cancellation.attach_process(process)
    try:
        if on_output is None or not hasattr(process, "communicate_streaming"):
            return process.communicate(timeout=timeout_seconds)
        return process.communicate_streaming(timeout=timeout_seconds, on_output=on_output)
    finally:
        if lease is not None:
            lease.attach_process(None)
        if cancellation is not None:
            cancellation.attach_process(None)


def make_run_record_output_callback(
    runtime_manager: RuntimeManager,
    record: WorkerRunRecord | None,
    *,
    extract_session: Callable[[str | None, str, str], str | None],
) -> Callable[[str, str, str, str], None]:
    def on_output(stream_name: str, chunk: str, stdout: str, stderr: str) -> None:
        session_id = extract_session(record.session_id if record is not None else None, stdout, stderr)
        update_worker_run_record(
            runtime_manager,
            record,
            session_id=session_id,
            stdout=stdout if stream_name == "stdout" else None,
            stderr=stderr if stream_name == "stderr" else None,
        )

    return on_output


def project_allows_conclude_fallback(client: CairnClient, project_id: str, *, worker_name: str, intent_id: str) -> bool:
    project = client.get_project(project_id)
    if project.project.status == "active":
        return True
    LOG.info(
        "skip conclude fallback because project is no longer active project=%s intent=%s worker=%s status=%s",
        project_id,
        intent_id,
        worker_name,
        project.project.status,
    )
    return False


def best_effort_release_reason(client: CairnClient, project_id: str, worker_name: str) -> None:
    response = client.release_reason(project_id, worker_name)
    if not response.ok and response.status_code not in (403, 409):
        LOG.warning(
            "reason release failed project=%s worker=%s status=%s",
            project_id,
            worker_name,
            response.status_code,
        )
    elif response.ok:
        LOG.info("released reason project=%s worker=%s", project_id, worker_name)
    else:
        LOG.info(
            "reason release skipped project=%s worker=%s status=%s",
            project_id,
            worker_name,
            response.status_code,
        )


def write_conclude_result(
    client: CairnClient,
    project_id: str,
    intent_id: str,
    worker_name: str,
    description: str,
    *,
    source: str,
    phase_ms: int,
    total_ms: int | None = None,
) -> str:
    return write_conclude_result_with_fact_id(
        client,
        project_id,
        intent_id,
        worker_name,
        description,
        source=source,
        phase_ms=phase_ms,
        total_ms=total_ms,
    ).status


def write_conclude_result_with_fact_id(
    client: CairnClient,
    project_id: str,
    intent_id: str,
    worker_name: str,
    description: str,
    *,
    source: str,
    phase_ms: int,
    total_ms: int | None = None,
) -> ConcludeWriteResult:
    response = client.conclude(project_id, intent_id, worker_name, description)
    if response.ok:
        fact_id: str | None = None
        if isinstance(response.data, dict):
            fact = response.data.get("fact")
            if isinstance(fact, dict):
                candidate = fact.get("id")
                if isinstance(candidate, str) and candidate:
                    fact_id = candidate
        if total_ms is None:
            LOG.info(
                "intent concluded project=%s intent=%s worker=%s source=%s phase_ms=%s",
                project_id,
                intent_id,
                worker_name,
                source,
                phase_ms,
            )
        else:
            LOG.info(
                "intent concluded project=%s intent=%s worker=%s source=%s phase_ms=%s total_ms=%s",
                project_id,
                intent_id,
                worker_name,
                source,
                phase_ms,
                total_ms,
            )
        return ConcludeWriteResult(status="success", fact_id=fact_id)
    if response.status_code == 403:
        LOG.info(
            "project became inactive during conclude project=%s intent=%s worker=%s",
            project_id,
            intent_id,
            worker_name,
        )
    else:
        LOG.warning(
            "conclude write failed project=%s intent=%s worker=%s status=%s body=%s",
            project_id,
            intent_id,
            worker_name,
            response.status_code,
            response.text,
        )
    best_effort_release(client, project_id, intent_id, worker_name)
    return ConcludeWriteResult(status="failed", fact_id=None)


def best_effort_release(client: CairnClient, project_id: str, intent_id: str, worker_name: str) -> None:
    response = client.release(project_id, intent_id, worker_name)
    if not response.ok and response.status_code not in (403, 409):
        LOG.warning(
            "release failed project=%s intent=%s worker=%s status=%s",
            project_id,
            intent_id,
            worker_name,
            response.status_code,
        )
    elif response.ok:
        LOG.info("released intent project=%s intent=%s worker=%s", project_id, intent_id, worker_name)
    else:
        LOG.info(
            "release skipped project=%s intent=%s worker=%s status=%s",
            project_id,
            intent_id,
            worker_name,
            response.status_code,
        )
