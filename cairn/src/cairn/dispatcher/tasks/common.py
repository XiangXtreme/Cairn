from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath

from cairn.dispatcher.config import WorkerConfig
from cairn.dispatcher.protocol.client import CairnClient
from cairn.dispatcher.runtime.cancellation import TaskCancellation
from cairn.dispatcher.runtime.heartbeat import HeartbeatLease
from cairn.dispatcher.runtime.manager import RuntimeManager
from cairn.dispatcher.runtime.process import ProcessResult

LOG_PREVIEW_LIMIT = 1200
GRAPH_SNAPSHOT_ROOT = "prompts"
OBSERVER_RUN_ROOT = "runs"
LOG = logging.getLogger(__name__)


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
    stdout_preview: str = ""
    stderr_preview: str = ""


def preview(text: str, limit: int = LOG_PREVIEW_LIMIT) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    record = WorkerRunRecord(
        run_id=uuid.uuid4().hex,
        project_id=project_id,
        intent_id=intent_id,
        phase=phase,
        worker_name=worker.name,
        agent_type=agent_type,
        workspace_name=workspace_name,
        workspace_path=str(runtime_manager.workspace_path(workspace_name)),
        session_id=session_id,
        status="running",
        started_at=started_at,
        updated_at=started_at,
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
    record.session_id = session_id or record.session_id
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
        "stdout_preview": record.stdout_preview,
        "stderr_preview": record.stderr_preview,
    }
    path = PurePath(OBSERVER_RUN_ROOT) / record.project_id / f"{record.run_id}.json"
    runtime_manager.write_observer_text_file(str(path), json.dumps(payload, ensure_ascii=False, indent=2))


def did_timeout(result: ProcessResult) -> bool:
    return not result.cancelled and (result.timed_out or result.returncode in (124, 137))


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
    process = runtime_manager.build_exec_process(
        workspace_name,
        dict(worker.env),
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
) -> ProcessResult:
    LOG.info(
        "starting worker process workspace=%s worker=%s phase=%s timeout=%ss",
        workspace_name,
        worker.name,
        phase,
        timeout_seconds,
    )
    process = runtime_manager.build_exec_process(
        workspace_name,
        dict(worker.env),
        argv,
        timeout_seconds=timeout_seconds,
    )
    process.start()
    if lease is not None:
        lease.attach_process(process)
    if cancellation is not None:
        cancellation.attach_process(process)
    try:
        return process.communicate(timeout=timeout_seconds)
    finally:
        if lease is not None:
            lease.attach_process(None)
        if cancellation is not None:
            cancellation.attach_process(None)


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
