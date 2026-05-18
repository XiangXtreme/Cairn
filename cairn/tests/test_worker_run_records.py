from __future__ import annotations

import json
from pathlib import Path

from cairn.dispatcher.config import ExecutionConfig, WorkerConfig
from cairn.dispatcher.runtime.local import LocalRuntimeManager
from cairn.dispatcher.tasks.common import extract_worker_skills, start_worker_run_record


def test_extract_worker_skills_reads_ids_names_and_paths() -> None:
    worker = WorkerConfig(
        name="codex_main",
        type="codex",
        enabled=True,
        task_types=["reason"],
        max_running=1,
        priority=0,
        env={
            "CODEX_MODEL": "gpt-5.5",
            "CODEX_BASE_URL": "https://ai.example.test/v1",
            "OPENAI_API_KEY": "sk-test",
            "CAIRN_SKILLS": json.dumps(
                [
                    {
                        "id": "cairn-web-surface",
                        "name": "Cairn Web Surface",
                        "path": "/repo/skills/cairn-web-surface",
                    },
                    {
                        "id": "cairn-creds-smb",
                        "name": "Cairn Creds SMB",
                        "path": "/repo/skills/cairn-creds-smb",
                    },
                ]
            )
        },
    )

    skill_ids, skill_names, skill_paths = extract_worker_skills(worker)

    assert skill_ids == ["cairn-web-surface", "cairn-creds-smb"]
    assert skill_names == ["Cairn Web Surface", "Cairn Creds SMB"]
    assert skill_paths == [
        "/repo/skills/cairn-web-surface",
        "/repo/skills/cairn-creds-smb",
    ]


def test_start_worker_run_record_persists_skill_metadata(tmp_path: Path) -> None:
    worker = WorkerConfig(
        name="codex_main",
        type="codex",
        enabled=True,
        task_types=["reason"],
        max_running=1,
        priority=0,
        env={
            "CODEX_MODEL": "gpt-5.5",
            "CODEX_BASE_URL": "https://ai.example.test/v1",
            "OPENAI_API_KEY": "sk-test",
            "CAIRN_SKILLS": json.dumps(
                [
                    {
                        "id": "cairn-agent-mcp-safety",
                        "name": "Cairn Agent MCP Safety",
                        "path": "/repo/skills/cairn-agent-mcp-safety",
                    }
                ]
            )
        },
    )
    runtime = LocalRuntimeManager(ExecutionConfig(backend="local", work_dir=tmp_path))
    workspace_name = runtime.ensure_running("proj_test")

    record = start_worker_run_record(
        runtime,
        project_id="proj_test",
        intent_id=None,
        phase="reason_execute",
        worker=worker,
        agent_type="codex",
        workspace_name=workspace_name,
        session_id="session-1",
    )

    run_path = tmp_path / "observer" / "runs" / "proj_test" / f"{record.run_id}.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    assert payload["skill_ids"] == ["cairn-agent-mcp-safety"]
    assert payload["skill_names"] == ["Cairn Agent MCP Safety"]
    assert payload["skill_source_paths"] == ["/repo/skills/cairn-agent-mcp-safety"]
