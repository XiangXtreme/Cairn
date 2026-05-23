from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime
import yaml

from cairn.server.db import get_conn
from cairn.server.services import (
    build_project_metadata,
    expire_reason_leases,
    expire_workers,
    get_project_or_404,
)

router = APIRouter(tags=["export"])


def format_export_timestamp(value: str | None) -> str | None:
    if not value:
        return value
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _load_project_data(conn, project_id: str):
    expire_workers(conn, project_id)
    expire_reason_leases(conn, project_id)
    proj = get_project_or_404(conn, project_id)

    facts = conn.execute(
        "SELECT id, description FROM facts WHERE project_id = ?", (project_id,)
    ).fetchall()
    hints = conn.execute(
        "SELECT content, creator, created_at FROM hints WHERE project_id = ? ORDER BY created_at",
        (project_id,),
    ).fetchall()
    intents = conn.execute(
        "SELECT * FROM intents WHERE project_id = ? ORDER BY created_at",
        (project_id,),
    ).fetchall()

    sources_by_intent = {}
    for i in intents:
        rows = conn.execute(
            "SELECT fact_id FROM intent_sources WHERE intent_id = ? AND project_id = ? ORDER BY rowid",
            (i["id"], project_id),
        ).fetchall()
        sources_by_intent[i["id"]] = [r["fact_id"] for r in rows]

    return proj, facts, hints, intents, sources_by_intent


def _export_yaml(conn, project_id: str) -> str:
    proj, facts, hints, intents, sources_by_intent = _load_project_data(conn, project_id)
    metadata = build_project_metadata(conn, project_id)

    origin_desc = ""
    goal_desc = ""
    for f in facts:
        if f["id"] == "origin":
            origin_desc = f["description"]
        elif f["id"] == "goal":
            goal_desc = f["description"]

    data: dict = {
        "project": {
            "title": proj["title"],
            "origin": origin_desc,
            "goal": goal_desc,
        }
    }
    if metadata.summary.content:
        data["project"]["summary"] = {
            "content": metadata.summary.content,
            "source": metadata.summary.source,
            "updated_at": format_export_timestamp(metadata.summary.updated_at),
        }

    if hints:
        data["hints"] = [
            {
                "content": h["content"],
                "creator": h["creator"],
                "created_at": format_export_timestamp(h["created_at"]),
            }
            for h in hints
        ]

    fact_list = []
    for f in facts:
        entry: dict = {"id": f["id"], "description": f["description"]}
        fact_meta = metadata.facts.get(f["id"])
        if fact_meta is not None:
            meta_entry: dict = {
                "kind": fact_meta.kind,
                "tags": fact_meta.tags,
                "summary": fact_meta.summary,
                "source": fact_meta.source,
                "updated_at": format_export_timestamp(fact_meta.updated_at),
            }
            if fact_meta.confidence is not None:
                meta_entry["confidence"] = fact_meta.confidence
            entry["metadata"] = {key: value for key, value in meta_entry.items() if value not in ("", [], None)}
        fact_list.append(entry)
    data["facts"] = fact_list

    intent_list = []
    for i in intents:
        entry: dict = {
            "id": i["id"],
            "from": sources_by_intent.get(i["id"], []),
            "to": i["to_fact_id"],
            "description": i["description"],
            "creator": i["creator"],
            "worker": i["worker"],
            "created_at": format_export_timestamp(i["created_at"]),
            "concluded_at": format_export_timestamp(i["concluded_at"]),
        }
        intent_meta = metadata.intents.get(i["id"])
        if intent_meta is not None:
            meta_entry = {
                "priority": intent_meta.priority,
                "policy_status": intent_meta.policy_status,
                "tags": intent_meta.tags,
                "summary": intent_meta.summary,
                "updated_at": format_export_timestamp(intent_meta.updated_at),
            }
            entry["metadata"] = {key: value for key, value in meta_entry.items() if value not in ("", [], None)}
        intent_list.append(entry)

    if intent_list:
        data["intents"] = intent_list

    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _export_timeline(conn, project_id: str) -> str:
    proj, facts, hints, intents, sources_by_intent = _load_project_data(conn, project_id)

    facts_by_id = {f["id"]: f["description"] for f in facts}

    events: list[tuple[str, int, str]] = []  # (timestamp, order, text)
    order = 0

    origin_desc = facts_by_id.get("origin", "")
    goal_desc = facts_by_id.get("goal", "")
    ts = format_export_timestamp(proj["created_at"]) or ""
    block = f"[{ts}] PROJECT CREATED\n  origin: {origin_desc}\n  goal: {goal_desc}"
    events.append((proj["created_at"] or "", order, block))
    order += 1

    for h in hints:
        ts = format_export_timestamp(h["created_at"]) or ""
        block = f"[{ts}] HINT by {h['creator']}\n  {h['content']}"
        events.append((h["created_at"] or "", order, block))
        order += 1

    for i in intents:
        src = sources_by_intent.get(i["id"], [])
        from_str = ", ".join(src)

        ts = format_export_timestamp(i["created_at"]) or ""
        meta = f"  from: {from_str}"
        if i["worker"] and not i["concluded_at"]:
            meta += f"\n  worker: {i['worker']} (in progress)"
        block = f"[{ts}] INTENT DECLARED {i['id']} by {i['creator']}\n{meta}\n  {i['description']}"
        events.append((i["created_at"] or "", order, block))
        order += 1

        if not i["concluded_at"] or not i["to_fact_id"]:
            continue

        ts = format_export_timestamp(i["concluded_at"]) or ""
        actor = i["worker"] or i["creator"]

        if i["to_fact_id"] == "goal":
            block = f"[{ts}] PROJECT COMPLETED by {actor}\n  via: {i['id']} from {from_str}"
        else:
            fact_desc = facts_by_id.get(i["to_fact_id"], "")
            block = f"[{ts}] INTENT CONCLUDED {i['id']} by {actor}\n  from: {from_str}\n  produced: {i['to_fact_id']}\n  {fact_desc}"

        events.append((i["concluded_at"] or "", order, block))
        order += 1

    events.sort(key=lambda e: (e[0], e[1]))

    return "\n\n".join(e[2] for e in events) + "\n"


@router.get("/projects/{project_id}/export")
def export_project(project_id: str, format: str = "yaml"):
    if format not in ("yaml", "timeline"):
        raise HTTPException(400, "Supported formats: yaml, timeline")

    with get_conn() as conn:
        if format == "timeline":
            text = _export_timeline(conn, project_id)
        else:
            text = _export_yaml(conn, project_id)

        return Response(content=text, media_type="text/plain")
