from __future__ import annotations

import shutil
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from cairn.server.dispatch_settings import resolve_dispatch_config_path
from cairn.server.models import (
    FactMetadata,
    Intent,
    IntentMetadata,
    ObserverCheckpoint,
    ProjectMeta,
    ProjectMetadata,
    ProjectReason,
    ProjectSummaryMetadata,
    UpdateFactMetadataRequest,
    UpdateIntentMetadataRequest,
    UpdateObserverCheckpointRequest,
    UpdateProjectSummaryRequest,
)

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_project_id(conn: sqlite3.Connection) -> str:
    conn.execute("UPDATE counters SET value = value + 1 WHERE name = 'project'")
    row = conn.execute("SELECT value FROM counters WHERE name = 'project'").fetchone()
    return f"proj_{row['value']:03d}"


def _next_scoped_id(
    conn: sqlite3.Connection, kind: str, prefix: str, project_id: str
) -> str:
    conn.execute(
        "INSERT OR IGNORE INTO scoped_counters (project_id, kind, value) VALUES (?, ?, 0)",
        (project_id, kind),
    )
    conn.execute(
        "UPDATE scoped_counters SET value = value + 1 WHERE project_id = ? AND kind = ?",
        (project_id, kind),
    )
    row = conn.execute(
        "SELECT value FROM scoped_counters WHERE project_id = ? AND kind = ?",
        (project_id, kind),
    ).fetchone()
    assert row is not None
    return f"{prefix}{row['value']:03d}"


def next_fact_id(conn: sqlite3.Connection, project_id: str) -> str:
    return _next_scoped_id(conn, "fact", "f", project_id)


def next_intent_id(conn: sqlite3.Connection, project_id: str) -> str:
    return _next_scoped_id(conn, "intent", "i", project_id)


def next_hint_id(conn: sqlite3.Connection, project_id: str) -> str:
    return _next_scoped_id(conn, "hint", "h", project_id)


def get_project_or_404(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Project not found")
    return row


def check_project_active(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = get_project_or_404(conn, project_id)
    if row["status"] != "active":
        raise HTTPException(403, f"Project is {row['status']}")
    return row


def check_project_hint_writable(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = get_project_or_404(conn, project_id)
    if row["status"] not in ("active", "stopped", "completed"):
        raise HTTPException(403, f"Project is {row['status']}")
    return row


def check_project_completed(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = get_project_or_404(conn, project_id)
    if row["status"] != "completed":
        raise HTTPException(403, f"Project is {row['status']}")
    return row


def validate_facts_exist(
    conn: sqlite3.Connection, project_id: str, fact_ids: list[str]
) -> None:
    for fid in fact_ids:
        row = conn.execute(
            "SELECT 1 FROM facts WHERE id = ? AND project_id = ?", (fid, project_id)
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"Fact {fid} not found")


def validate_fact_exists(conn: sqlite3.Connection, project_id: str, fact_id: str) -> None:
    validate_facts_exist(conn, project_id, [fact_id])


def validate_goal_not_in_sources(fact_ids: list[str]) -> None:
    if "goal" in fact_ids:
        raise HTTPException(400, "goal cannot be used in from")


def validate_intent_creator_worker(creator: str, worker: str | None) -> None:
    if worker is not None and worker != creator:
        raise HTTPException(400, "worker must be null or equal to creator")


def get_intent_or_404(
    conn: sqlite3.Connection, project_id: str, intent_id: str
) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM intents WHERE id = ? AND project_id = ?",
        (intent_id, project_id),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Intent not found")
    return row


def _load_tags(value: str) -> list[str]:
    try:
        payload = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in payload:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def fact_metadata_from_row(row: sqlite3.Row) -> FactMetadata:
    return FactMetadata(
        fact_id=row["fact_id"],
        kind=row["kind"],
        confidence=row["confidence"],
        tags=_load_tags(row["tags_json"]),
        summary=row["summary"],
        source=row["source"],
        updated_at=row["updated_at"],
    )


def intent_metadata_from_row(row: sqlite3.Row) -> IntentMetadata:
    return IntentMetadata(
        intent_id=row["intent_id"],
        priority=row["priority"],
        policy_status=row["policy_status"],
        tags=_load_tags(row["tags_json"]),
        summary=row["summary"],
        updated_at=row["updated_at"],
    )


def build_project_metadata(conn: sqlite3.Connection, project_id: str) -> ProjectMetadata:
    get_project_or_404(conn, project_id)
    fact_rows = conn.execute(
        "SELECT * FROM fact_metadata WHERE project_id = ? ORDER BY fact_id",
        (project_id,),
    ).fetchall()
    intent_rows = conn.execute(
        "SELECT * FROM intent_metadata WHERE project_id = ? ORDER BY intent_id",
        (project_id,),
    ).fetchall()
    summary_row = conn.execute(
        "SELECT * FROM project_summaries WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    checkpoint_row = conn.execute(
        "SELECT * FROM observer_checkpoints WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    summary = (
        ProjectSummaryMetadata(
            content=summary_row["content"],
            source=summary_row["source"],
            updated_at=summary_row["updated_at"],
        )
        if summary_row is not None
        else ProjectSummaryMetadata()
    )
    observer = (
        ObserverCheckpoint(
            last_digest=checkpoint_row["last_digest"],
            last_observed_at=checkpoint_row["last_observed_at"],
        )
        if checkpoint_row is not None
        else ObserverCheckpoint()
    )
    return ProjectMetadata(
        project_id=project_id,
        summary=summary,
        facts={row["fact_id"]: fact_metadata_from_row(row) for row in fact_rows},
        intents={row["intent_id"]: intent_metadata_from_row(row) for row in intent_rows},
        observer=observer,
    )


def upsert_fact_metadata(
    conn: sqlite3.Connection,
    project_id: str,
    fact_id: str,
    body: UpdateFactMetadataRequest,
) -> FactMetadata:
    get_project_or_404(conn, project_id)
    validate_fact_exists(conn, project_id, fact_id)
    now = utcnow()
    tags_json = json.dumps(body.tags, ensure_ascii=False, separators=(",", ":"))
    conn.execute(
        """
        INSERT INTO fact_metadata (project_id, fact_id, kind, confidence, tags_json, summary, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, fact_id) DO UPDATE SET
            kind = excluded.kind,
            confidence = excluded.confidence,
            tags_json = excluded.tags_json,
            summary = excluded.summary,
            source = excluded.source,
            updated_at = excluded.updated_at
        """,
        (
            project_id,
            fact_id,
            body.kind,
            body.confidence,
            tags_json,
            body.summary,
            body.source,
            now,
        ),
    )
    row = conn.execute(
        "SELECT * FROM fact_metadata WHERE project_id = ? AND fact_id = ?",
        (project_id, fact_id),
    ).fetchone()
    assert row is not None
    return fact_metadata_from_row(row)


def upsert_intent_metadata(
    conn: sqlite3.Connection,
    project_id: str,
    intent_id: str,
    body: UpdateIntentMetadataRequest,
) -> IntentMetadata:
    get_project_or_404(conn, project_id)
    get_intent_or_404(conn, project_id, intent_id)
    now = utcnow()
    tags_json = json.dumps(body.tags, ensure_ascii=False, separators=(",", ":"))
    conn.execute(
        """
        INSERT INTO intent_metadata (project_id, intent_id, priority, policy_status, tags_json, summary, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, intent_id) DO UPDATE SET
            priority = excluded.priority,
            policy_status = excluded.policy_status,
            tags_json = excluded.tags_json,
            summary = excluded.summary,
            updated_at = excluded.updated_at
        """,
        (
            project_id,
            intent_id,
            body.priority,
            body.policy_status,
            tags_json,
            body.summary,
            now,
        ),
    )
    row = conn.execute(
        "SELECT * FROM intent_metadata WHERE project_id = ? AND intent_id = ?",
        (project_id, intent_id),
    ).fetchone()
    assert row is not None
    return intent_metadata_from_row(row)


def upsert_project_summary(
    conn: sqlite3.Connection,
    project_id: str,
    body: UpdateProjectSummaryRequest,
) -> ProjectSummaryMetadata:
    get_project_or_404(conn, project_id)
    now = utcnow()
    conn.execute(
        """
        INSERT INTO project_summaries (project_id, content, source, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
            content = excluded.content,
            source = excluded.source,
            updated_at = excluded.updated_at
        """,
        (project_id, body.content, body.source, now),
    )
    return ProjectSummaryMetadata(content=body.content, source=body.source, updated_at=now)


def upsert_observer_checkpoint(
    conn: sqlite3.Connection,
    project_id: str,
    body: UpdateObserverCheckpointRequest,
) -> ObserverCheckpoint:
    get_project_or_404(conn, project_id)
    now = utcnow()
    conn.execute(
        """
        INSERT INTO observer_checkpoints (project_id, last_digest, last_observed_at)
        VALUES (?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
            last_digest = excluded.last_digest,
            last_observed_at = excluded.last_observed_at
        """,
        (project_id, body.last_digest, now),
    )
    return ObserverCheckpoint(last_digest=body.last_digest, last_observed_at=now)


def get_claimable_open_intent_or_404(
    conn: sqlite3.Connection, project_id: str, intent_id: str, worker: str
) -> sqlite3.Row:
    expire_workers(conn, project_id)
    row = get_intent_or_404(conn, project_id, intent_id)
    if row["to_fact_id"] is not None:
        raise HTTPException(409, "Intent already concluded")
    if row["worker"] is not None and row["worker"] != worker:
        raise HTTPException(409, f"Intent is currently claimed by {row['worker']}")
    return row


def get_releasable_open_intent_or_404(
    conn: sqlite3.Connection, project_id: str, intent_id: str, worker: str
) -> sqlite3.Row:
    expire_workers(conn, project_id)
    row = get_intent_or_404(conn, project_id, intent_id)
    if row["to_fact_id"] is not None:
        raise HTTPException(409, "Intent already concluded")
    if row["worker"] is None:
        return row
    if row["worker"] != worker:
        raise HTTPException(409, f"Intent is currently claimed by {row['worker']}")
    return row


def get_completion_intent_or_409(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    rows = conn.execute(
        "SELECT * FROM intents WHERE project_id = ? AND to_fact_id = 'goal'",
        (project_id,),
    ).fetchall()
    if not rows:
        raise HTTPException(409, "Completed project is missing its completion intent")
    if len(rows) != 1:
        raise HTTPException(409, "Completed project has multiple completion intents")
    return rows[0]


def intent_to_model(conn: sqlite3.Connection, row: sqlite3.Row, project_id: str) -> Intent:
    sources = conn.execute(
        "SELECT fact_id FROM intent_sources WHERE intent_id = ? AND project_id = ? ORDER BY rowid",
        (row["id"], project_id),
    ).fetchall()
    return Intent(
        id=row["id"],
        **{"from": [s["fact_id"] for s in sources]},
        to=row["to_fact_id"],
        description=row["description"],
        creator=row["creator"],
        worker=row["worker"],
        last_heartbeat_at=row["last_heartbeat_at"],
        created_at=row["created_at"],
        concluded_at=row["concluded_at"],
    )


def build_intents(conn: sqlite3.Connection, project_id: str) -> list[Intent]:
    rows = conn.execute(
        "SELECT * FROM intents WHERE project_id = ? ORDER BY created_at",
        (project_id,),
    ).fetchall()
    return [intent_to_model(conn, r, project_id) for r in rows]


def get_intent_timeout(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT intent_timeout FROM settings WHERE rowid = 1").fetchone()
    return row["intent_timeout"]


def get_reason_timeout(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT reason_timeout FROM settings WHERE rowid = 1").fetchone()
    return row["reason_timeout"]


def project_reason_from_row(row: sqlite3.Row) -> ProjectReason | None:
    if row["reason_worker"] is None:
        return None
    return ProjectReason(
        worker=row["reason_worker"],
        trigger=row["reason_trigger"],
        started_at=row["reason_started_at"],
        last_heartbeat_at=row["reason_last_heartbeat_at"],
    )


def project_meta_from_row(row: sqlite3.Row) -> ProjectMeta:
    return ProjectMeta(
        id=row["id"],
        title=row["title"],
        status=row["status"],
        created_at=row["created_at"],
        reason=project_reason_from_row(row),
    )


def clear_project_reason(conn: sqlite3.Connection, project_id: str) -> None:
    conn.execute(
        """
        UPDATE projects
        SET reason_worker = NULL,
            reason_trigger = NULL,
            reason_started_at = NULL,
            reason_last_heartbeat_at = NULL
        WHERE id = ?
        """,
        (project_id,),
    )


def delete_project_artifacts(project_id: str) -> None:
    for path in project_artifact_paths(project_id):
        shutil.rmtree(path, ignore_errors=True)


def project_artifact_paths(project_id: str) -> list[Path]:
    work_dir = _resolve_runtime_work_dir()
    project_name = _sanitize_workspace_name(project_id)
    return [
        work_dir / "observer" / "runs" / project_id,
        work_dir / "projects" / project_name,
    ]


def _resolve_runtime_work_dir() -> Path:
    config_path = resolve_dispatch_config_path()
    if not config_path.exists():
        return Path(".cairn-runtime").resolve()
    try:
        import yaml

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return Path(".cairn-runtime").resolve()

    execution = raw.get("execution")
    if not isinstance(execution, dict):
        return Path(".cairn-runtime").resolve()
    work_dir = execution.get("work_dir")
    if not isinstance(work_dir, str) or not work_dir.strip():
        return Path(".cairn-runtime").resolve()
    return (config_path.parent / work_dir).resolve()


def _sanitize_workspace_name(value: str) -> str:
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in "_.-":
            cleaned.append(ch)
        else:
            cleaned.append("-")
    text = "".join(cleaned).strip(".-")
    return text or "project"


def expire_workers(conn: sqlite3.Connection, project_id: str | None = None) -> None:
    timeout = get_intent_timeout(conn)
    now = utcnow()
    query = """
        UPDATE intents
        SET worker = NULL
        WHERE to_fact_id IS NULL
          AND worker IS NOT NULL
          AND last_heartbeat_at IS NOT NULL
          AND (julianday(?) - julianday(last_heartbeat_at)) * 86400 > ?
    """
    params: tuple = (now, timeout)
    if project_id is not None:
        query = query.replace("WHERE ", "WHERE project_id = ? AND ", 1)
        params = (project_id, now, timeout)
    conn.execute(query, params)


def expire_reason_leases(conn: sqlite3.Connection, project_id: str | None = None) -> None:
    timeout = get_reason_timeout(conn)
    now = utcnow()
    query = """
        UPDATE projects
        SET reason_worker = NULL,
            reason_trigger = NULL,
            reason_started_at = NULL,
            reason_last_heartbeat_at = NULL
        WHERE reason_worker IS NOT NULL
          AND reason_last_heartbeat_at IS NOT NULL
          AND (julianday(?) - julianday(reason_last_heartbeat_at)) * 86400 > ?
    """
    params: tuple = (now, timeout)
    if project_id is not None:
        query = query.replace("WHERE ", "WHERE id = ? AND ", 1)
        params = (project_id, now, timeout)
    conn.execute(query, params)
