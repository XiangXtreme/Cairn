from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cairn.server import db
from cairn.server.app import app


def _client(tmp_path: Path) -> TestClient:
    db._db_path = None
    db.configure(tmp_path / "cairn.db")
    return TestClient(app)


def test_metadata_crud_and_export_yaml(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/projects",
        json={"title": "demo", "origin": "target", "goal": "flag"},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["project"]["id"]

    empty = client.get(f"/projects/{project_id}/metadata")
    assert empty.status_code == 200
    assert empty.json()["facts"] == {}
    assert empty.json()["intents"] == {}
    assert empty.json()["summary"]["content"] == ""

    intent = client.post(
        f"/projects/{project_id}/intents",
        json={"from": ["origin"], "description": "check web surface", "creator": "tester", "worker": None},
    )
    assert intent.status_code == 201, intent.text
    intent_id = intent.json()["id"]

    fact_meta = client.patch(
        f"/projects/{project_id}/facts/origin/metadata",
        json={
            "kind": "evidence",
            "confidence": 0.8,
            "tags": ["web", "web", ""],
            "summary": "HTTP target is in scope",
            "source": "test",
        },
    )
    assert fact_meta.status_code == 200, fact_meta.text
    assert fact_meta.json()["tags"] == ["web"]

    intent_meta = client.patch(
        f"/projects/{project_id}/intents/{intent_id}/metadata",
        json={
            "priority": 10,
            "policy_status": "paused",
            "tags": ["low-signal"],
            "summary": "superseded by a stronger route",
        },
    )
    assert intent_meta.status_code == 200, intent_meta.text

    summary = client.put(
        f"/projects/{project_id}/summary",
        json={"content": "Current state is compact.", "source": "observer.test"},
    )
    assert summary.status_code == 200, summary.text

    metadata = client.get(f"/projects/{project_id}/metadata").json()
    assert metadata["summary"]["content"] == "Current state is compact."
    assert metadata["facts"]["origin"]["kind"] == "evidence"
    assert metadata["intents"][intent_id]["policy_status"] == "paused"

    exported = client.get(f"/projects/{project_id}/export", params={"format": "yaml"})
    assert exported.status_code == 200
    assert "summary:" in exported.text
    assert "policy_status: paused" in exported.text
    assert "kind: evidence" in exported.text


def test_metadata_rejects_invalid_status_and_unknown_targets(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/projects",
        json={"title": "demo", "origin": "target", "goal": "flag"},
    )
    project_id = created.json()["project"]["id"]

    invalid = client.patch(
        f"/projects/{project_id}/intents/i999/metadata",
        json={"priority": 0, "policy_status": "done", "tags": [], "summary": ""},
    )
    assert invalid.status_code == 422

    missing = client.patch(
        f"/projects/{project_id}/facts/f999/metadata",
        json={"kind": "fact", "confidence": None, "tags": [], "summary": "", "source": ""},
    )
    assert missing.status_code == 404
