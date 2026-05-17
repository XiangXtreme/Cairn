from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cairn.server import db
from cairn.server.app import app


def test_delete_project_removes_runtime_artifacts(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    dispatch_path.write_text(
        "\n".join(
            [
                "server: http://example.test",
                "runtime:",
                "  interval: 3",
                "  max_workers: 1",
                "  max_running_projects: 1",
                "  max_project_workers: 1",
                "  healthcheck_timeout: 20",
                "  prompt_group: default",
                "tasks:",
                "  bootstrap:",
                "    timeout: 300",
                "    conclude_timeout: 90",
                "  reason:",
                "    timeout: 300",
                "    max_intents: 1",
                "  explore:",
                "    timeout: 300",
                "    conclude_timeout: 90",
                "execution:",
                "  backend: local",
                "  work_dir: .cairn-runtime",
                "workers:",
                "  - name: mock_worker",
                "    type: mock",
                "    enabled: true",
                "    task_types: [bootstrap]",
                "    max_running: 1",
                "    priority: 0",
                "    env: {}",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))

    runs_dir = tmp_path / ".cairn-runtime" / "observer" / "runs" / "proj_001"
    workspace_dir = tmp_path / ".cairn-runtime" / "projects" / "proj_001"
    runs_dir.mkdir(parents=True)
    workspace_dir.mkdir(parents=True)
    (runs_dir / "run.json").write_text("{}", encoding="utf-8")
    (workspace_dir / "notes.txt").write_text("keep out", encoding="utf-8")

    client = TestClient(app)
    create = client.post(
        "/projects",
        json={
            "title": "test",
            "origin": "origin",
            "goal": "goal",
        },
    )
    assert create.status_code == 201
    assert create.json()["project"]["id"] == "proj_001"

    response = client.delete("/projects/proj_001")
    assert response.status_code == 204

    with db.get_conn() as conn:
        project = conn.execute(
            "SELECT id FROM projects WHERE id = ?",
            ("proj_001",),
        ).fetchone()
        facts = conn.execute(
            "SELECT COUNT(*) AS count FROM facts WHERE project_id = ?",
            ("proj_001",),
        ).fetchone()

    assert project is None
    assert facts["count"] == 0
    assert not runs_dir.exists()
    assert not workspace_dir.exists()
