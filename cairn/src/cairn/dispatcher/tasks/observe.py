from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from cairn.dispatcher.config import DispatchConfig, WorkerConfig
from cairn.dispatcher.contracts import parse_observe_output
from cairn.dispatcher.prompting import load_prompt, render_prompt
from cairn.dispatcher.protocol.client import CairnClient
from cairn.dispatcher.runtime.cancellation import TaskCancellation
from cairn.dispatcher.runtime.manager import RuntimeManager
from cairn.dispatcher.tasks.common import (
    cancel_reason,
    did_timeout,
    extract_worker_skills,
    finish_worker_run_record,
    make_run_record_output_callback,
    preview,
    run_healthcheck,
    run_worker_process,
    start_worker_run_record,
    write_graph_snapshot_reference,
)
from cairn.dispatcher.workers.registry import get_driver
from cairn.server.models import ProjectDetail, ProjectMetadata

LOG = logging.getLogger(__name__)
OBSERVER_CREATOR_PREFIX = "observer"


def read_recent_worker_runs(work_dir: Path, project_id: str, limit: int) -> list[dict[str, Any]]:
    runs_root = work_dir.resolve() / "observer" / "runs" / project_id
    if not runs_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(runs_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            LOG.warning("skipping unreadable worker run record path=%s", path)
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("phase", "")).startswith("observe"):
            continue
        records.append(_compact_run_record(payload))
    records.sort(key=lambda item: str(item.get("updated_at") or item.get("started_at") or ""))
    return records[-limit:]


def build_observe_digest(
    project: ProjectDetail,
    export_yaml: str,
    metadata: ProjectMetadata,
    recent_runs: list[dict[str, Any]],
) -> str:
    payload = {
        "project_id": project.project.id,
        "status": project.project.status,
        "fact_ids": [fact.id for fact in project.facts],
        "intent_ids": [intent.id for intent in project.intents],
        "hint_ids": [hint.id for hint in project.hints],
        "graph": export_yaml,
        "metadata": {
            "summary": metadata.summary.model_dump(mode="json"),
            "facts": {key: value.model_dump(mode="json") for key, value in metadata.facts.items()},
            "intents": {key: value.model_dump(mode="json") for key, value in metadata.intents.items()},
        },
        "recent_runs": recent_runs,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_observe_task(
    config: DispatchConfig,
    client: CairnClient,
    runtime_manager: RuntimeManager,
    project: ProjectDetail,
    export_yaml: str,
    timeline: str,
    metadata: ProjectMetadata,
    recent_runs: list[dict[str, Any]],
    digest: str,
    worker: WorkerConfig,
    cancellation: TaskCancellation,
) -> str:
    driver = get_driver(worker.type)
    task_started = time.perf_counter()
    healthcheck_timeout = config.runtime.healthcheck_timeout
    workspace_name = runtime_manager.ensure_running(project.project.id)

    LOG.info(
        "starting worker process project=%s worker=%s phase=observe_healthcheck timeout=%ss skills=%s",
        project.project.id,
        worker.name,
        healthcheck_timeout,
        ",".join(extract_worker_skills(worker)[0]) or "-",
    )
    healthcheck = run_healthcheck(
        runtime_manager,
        workspace_name,
        worker,
        driver.build_healthcheck(worker),
        timeout_seconds=healthcheck_timeout,
        cancellation=cancellation,
    )
    cancelled = cancel_reason(healthcheck.result, cancellation)
    if cancelled is not None:
        LOG.info("observe cancelled during healthcheck project=%s worker=%s reason=%s", project.project.id, worker.name, cancelled)
        return "cancelled"
    if healthcheck.result.returncode != 0:
        LOG.warning(
            "worker unhealthy project=%s worker=%s healthcheck_ms=%s stderr=%s",
            project.project.id,
            worker.name,
            healthcheck.duration_ms,
            preview(healthcheck.result.stderr),
        )
        return "unhealthy"

    prompt = render_prompt(
        load_prompt(config.runtime.prompt_group, "observe.md"),
        {
            "graph_yaml": write_graph_snapshot_reference(
                runtime_manager,
                workspace_name,
                export_yaml.strip(),
                phase="observe_execute",
            ),
            "timeline": timeline.strip(),
            "metadata_json": metadata.model_dump_json(indent=2),
            "recent_runs": json.dumps(recent_runs, ensure_ascii=False, indent=2),
            "max_updates": str(config.tasks.observe.max_updates),
        },
    )

    session = driver.prepare_session()
    command = driver.build_execute(worker, prompt, session)
    session = command.session
    execute_started = time.perf_counter()
    run_record = start_worker_run_record(
        runtime_manager,
        project_id=project.project.id,
        intent_id=None,
        phase="observe_execute",
        worker=worker,
        agent_type=worker.type,
        workspace_name=workspace_name,
        session_id=session,
    )
    result = run_worker_process(
        runtime_manager,
        workspace_name,
        worker,
        command.argv,
        phase="observe_execute",
        timeout_seconds=config.tasks.observe.timeout,
        cancellation=cancellation,
        on_output=make_run_record_output_callback(
            runtime_manager,
            run_record,
            extract_session=driver.extract_session,
        ),
    )
    execute_ms = int((time.perf_counter() - execute_started) * 1000)
    total_ms = int((time.perf_counter() - task_started) * 1000)
    session = driver.extract_session(session, result.stdout, result.stderr)
    finish_worker_run_record(runtime_manager, run_record, result, started=execute_started, session_id=session)
    cancelled = cancel_reason(result, cancellation)
    if cancelled is not None:
        LOG.info("observe cancelled project=%s worker=%s reason=%s execute_ms=%s", project.project.id, worker.name, cancelled, execute_ms)
        return "cancelled"
    if did_timeout(result):
        LOG.warning(
            "observe timed out project=%s worker=%s execute_ms=%s total_ms=%s stdout_preview=%s stderr_preview=%s",
            project.project.id,
            worker.name,
            execute_ms,
            total_ms,
            preview(result.stdout),
            preview(result.stderr),
        )
        return "failed"
    if result.returncode != 0:
        LOG.warning(
            "observe command failed project=%s worker=%s code=%s execute_ms=%s total_ms=%s stdout_preview=%s stderr_preview=%s",
            project.project.id,
            worker.name,
            result.returncode,
            execute_ms,
            total_ms,
            preview(result.stdout),
            preview(result.stderr),
        )
        return "failed"
    try:
        model_output = driver.extract_response_text(result.stdout, result.stderr)
        kind, data = parse_observe_output(model_output, max_updates=config.tasks.observe.max_updates)
    except Exception as exc:
        LOG.warning(
            "observe parse failed project=%s worker=%s error=%s execute_ms=%s total_ms=%s stdout_preview=%s stderr_preview=%s",
            project.project.id,
            worker.name,
            exc,
            execute_ms,
            total_ms,
            preview(result.stdout),
            preview(result.stderr),
        )
        return "failed"
    if kind == "rejected":
        LOG.warning("observe rejected project=%s worker=%s execute_ms=%s total_ms=%s", project.project.id, worker.name, execute_ms, total_ms)
        return "rejected"
    if kind == "noop" or data is None:
        checkpoint = client.update_observer_checkpoint(project.project.id, digest)
        if not checkpoint.ok:
            LOG.warning("observer checkpoint write failed project=%s worker=%s status=%s body=%s", project.project.id, worker.name, checkpoint.status_code, checkpoint.text)
            return "failed"
        LOG.info("observe finished without graph maintenance project=%s worker=%s execute_ms=%s total_ms=%s", project.project.id, worker.name, execute_ms, total_ms)
        return "success"

    applied = _apply_observer_updates(client, project, data, worker.name)
    if not applied:
        return "failed"
    checkpoint = client.update_observer_checkpoint(project.project.id, digest)
    if not checkpoint.ok:
        LOG.warning("observer checkpoint write failed project=%s worker=%s status=%s body=%s", project.project.id, worker.name, checkpoint.status_code, checkpoint.text)
        return "failed"
    LOG.info(
        "observe applied maintenance project=%s worker=%s fact_updates=%s intent_updates=%s hint=%s summary=%s execute_ms=%s total_ms=%s",
        project.project.id,
        worker.name,
        len(data.get("fact_metadata") or []),
        len(data.get("intent_metadata") or []),
        bool(data.get("hint")),
        bool(data.get("project_summary")),
        execute_ms,
        total_ms,
    )
    return "success"


def _compact_run_record(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "project_id",
        "intent_id",
        "phase",
        "worker_name",
        "agent_type",
        "status",
        "started_at",
        "updated_at",
        "ended_at",
        "exit_code",
        "timed_out",
        "cancelled",
        "cancel_reason",
        "duration_ms",
        "skill_ids",
        "stdout_preview",
        "stderr_preview",
    )
    return {key: payload.get(key) for key in keys if key in payload}


def _apply_observer_updates(
    client: CairnClient,
    project: ProjectDetail,
    data: dict[str, Any],
    worker_name: str,
) -> bool:
    fact_ids = {fact.id for fact in project.facts}
    intent_ids = {intent.id for intent in project.intents}
    creator = f"{OBSERVER_CREATOR_PREFIX}.{worker_name}"

    hint = data.get("hint")
    if hint:
        response = client.create_hint(project.project.id, hint["content"], creator)
        if not response.ok:
            LOG.warning("observer hint write failed project=%s status=%s body=%s", project.project.id, response.status_code, response.text)
            return False

    project_summary = data.get("project_summary")
    if project_summary:
        response = client.update_project_summary(
            project.project.id,
            project_summary["content"],
            project_summary.get("source") or creator,
        )
        if not response.ok:
            LOG.warning("observer project summary write failed project=%s status=%s body=%s", project.project.id, response.status_code, response.text)
            return False

    for item in data.get("fact_metadata") or []:
        fact_id = item["fact_id"]
        if fact_id not in fact_ids:
            LOG.warning("observer referenced unknown fact project=%s fact=%s", project.project.id, fact_id)
            return False
        payload = {key: value for key, value in item.items() if key != "fact_id"}
        response = client.update_fact_metadata(project.project.id, fact_id, payload)
        if not response.ok:
            LOG.warning("observer fact metadata write failed project=%s fact=%s status=%s body=%s", project.project.id, fact_id, response.status_code, response.text)
            return False

    for item in data.get("intent_metadata") or []:
        intent_id = item["intent_id"]
        if intent_id not in intent_ids:
            LOG.warning("observer referenced unknown intent project=%s intent=%s", project.project.id, intent_id)
            return False
        payload = {key: value for key, value in item.items() if key != "intent_id"}
        response = client.update_intent_metadata(project.project.id, intent_id, payload)
        if not response.ok:
            LOG.warning("observer intent metadata write failed project=%s intent=%s status=%s body=%s", project.project.id, intent_id, response.status_code, response.text)
            return False
    return True
