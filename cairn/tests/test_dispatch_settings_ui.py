from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cairn.server import db
from cairn.server.app import app


def _write_dispatch(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "server: http://example.test",
                "runtime:",
                "  interval: 3",
                "  max_workers: 2",
                "  max_running_projects: 2",
                "  max_project_workers: 2",
                "  healthcheck_timeout: 20",
                "  prompt_group: default",
                "tasks:",
                "  bootstrap:",
                "    timeout: 300",
                "    conclude_timeout: 90",
                "  reason:",
                "    timeout: 300",
                "    max_intents: 1",
                "    allow_unavailable_dispatch: false",
                "    unavailable_fact_limit: 2",
                "  explore:",
                "    timeout: 300",
                "    conclude_timeout: 90",
                "execution:",
                "  backend: local",
                "  work_dir: .cairn-runtime",
                "workers:",
                "  - name: codex_main",
                "    type: codex",
                "    enabled: true",
                "    task_types: [bootstrap, reason, explore]",
                "    max_running: 1",
                "    priority: 0",
                "    env:",
                "      CODEX_MODEL: gpt-5.4",
                "      CODEX_BASE_URL: https://api.openai.com/v1",
                "      OPENAI_API_KEY: sk-old",
            ]
        ),
        encoding="utf-8",
    )


def test_ui_dispatch_settings_bundle_and_compiled_yaml(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    client = TestClient(app)

    payload = client.get("/settings/dispatch?mode=ui")
    assert payload.status_code == 200
    data = payload.json()
    assert data["mode"] == "ui"
    assert data["workers"][0]["name"] == "codex_main"
    assert data["providers"][0]["id"] == "codex_main_provider"
    assert data["mode_info"]["source_path"].endswith("dispatch_ui")
    assert data["mode_info"]["compiled_path"].endswith("dispatch_ui.yaml")

    update = {
        "mode": "ui",
        "runtime": data["runtime"],
        "tasks": data["tasks"],
        "providers": [
            {
                **data["providers"][0],
                "model": "gpt-5.5",
                "base_url": "https://ai.example.test/v1",
                "auth_token": "sk-new",
            },
            {
                "id": "pi_shared",
                "name": "Pi Shared",
                "enabled": True,
                "kind": "pi",
                "model": "qwen3-coder-plus",
                "base_url": "https://pi.example.test/v1",
                "auth_token": "pi-token",
                "has_auth_token": False,
                "provider_api": "openai-completions",
                "context_window": 262144,
                "extra_env": {"PI_DIR": "/tmp/pi"},
            },
        ],
        "workers": [
                {
                    **data["workers"][0],
                    "provider_id": "codex_main_provider",
                    "mcp_server_ids": ["context7"],
                    "skill_ids": ["review"],
                    "mcp_supported": True,
                    "skill_supported": True,
                },
            {
                "source_name": "",
                "name": "pi_idle",
                "enabled": False,
                "type": "pi",
                "task_types": ["reason"],
                "max_running": 1,
                "priority": 1,
                "provider_id": "pi_shared",
                "provider_supported": True,
                "model": "",
                "base_url": "",
                "auth_token": "",
                "has_auth_token": False,
                "provider_api": "",
                "context_window": None,
                "mcp_server_ids": [],
                "skill_ids": [],
                "mcp_supported": False,
                "skill_supported": False,
            },
        ],
        "mcp_servers": [
            {
                "id": "context7",
                "name": "Context7",
                "enabled": True,
                "transport": "stdio",
                "command": "npx",
                "url": "",
                "args": ["-y", "@upstash/context7-mcp"],
                "env": {"FOO": "bar"},
            }
        ],
        "skills": [
            {
                "id": "review",
                "name": "Review",
                "enabled": True,
                "path": "/tmp/review-skill",
                "description": "placeholder",
                "enabled_claude": False,
                "enabled_codex": True,
            }
        ],
        "worker_bindings": [
                {
                    "worker_name": "codex_main",
                    "mcp_server_ids": ["context7"],
                    "skill_ids": ["review"],
                },
            {
                "worker_name": "pi_idle",
                "mcp_server_ids": [],
                "skill_ids": ["review"],
            },
        ],
    }

    saved = client.put("/settings/dispatch", json=update)
    assert saved.status_code == 200, saved.text
    saved_data = saved.json()
    assert saved_data["providers"][0]["model"] == "gpt-5.5"
    assert saved_data["workers"][0]["provider_id"] == "codex_main_provider"
    assert saved_data["mcp_servers"][0]["id"] == "context7"
    assert saved_data["skills"][0]["id"] == "review"
    assert saved_data["skills"][0]["enabled_codex"] is True

    bundle_root = tmp_path / "datas" / "cairn" / "dispatch_ui"
    compiled_path = tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"
    assert bundle_root.exists()
    assert compiled_path.exists()
    assert (bundle_root / "workers.json").exists()
    assert (bundle_root / "providers.json").exists()
    assert (bundle_root / "mcp_servers.json").exists()
    assert (bundle_root / "skills.json").exists()
    assert (bundle_root / "worker_bindings.json").exists()

    workers_json = json.loads((bundle_root / "workers.json").read_text(encoding="utf-8"))
    providers_json = json.loads((bundle_root / "providers.json").read_text(encoding="utf-8"))
    assert providers_json[0]["model"] == "gpt-5.5"
    assert workers_json[0]["mcp_server_ids"] == ["context7"]

    compiled = compiled_path.read_text(encoding="utf-8")
    assert "CODEX_MODEL: gpt-5.5" in compiled
    assert "CODEX_BASE_URL: https://ai.example.test/v1" in compiled
    assert "OPENAI_API_KEY: sk-new" in compiled
    assert "PI_MODEL: qwen3-coder-plus" in compiled
    assert "CAIRN_MCP_SERVERS:" in compiled
    assert '"enabled_codex":true' in compiled
    assert "name: pi_idle" in compiled
    assert "enabled: false" in compiled


def test_ui_dispatch_settings_preserves_auth_token_when_secret_field_is_blank(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    client = TestClient(app)
    initial = client.get("/settings/dispatch?mode=ui")
    assert initial.status_code == 200
    payload = initial.json()

    payload["providers"][0]["auth_token"] = "sk-first"
    payload["providers"][0]["has_auth_token"] = True
    payload["workers"][0]["provider_id"] = payload["providers"][0]["id"]
    first_save = client.put("/settings/dispatch", json=payload)
    assert first_save.status_code == 200, first_save.text

    second_payload = first_save.json()
    second_payload["providers"][0]["auth_token"] = ""
    second_payload["providers"][0]["has_auth_token"] = True
    second_payload["providers"][0]["model"] = "gpt-5.5"

    second_save = client.put("/settings/dispatch", json=second_payload)
    assert second_save.status_code == 200, second_save.text

    bundle_root = tmp_path / "datas" / "cairn" / "dispatch_ui"
    providers_json = json.loads((bundle_root / "providers.json").read_text(encoding="utf-8"))
    assert providers_json[0]["auth_token"] == "sk-first"

    compiled = (tmp_path / "datas" / "cairn" / "dispatch_ui.yaml").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY: sk-first" in compiled
    assert "CODEX_MODEL: gpt-5.5" in compiled


def test_disabled_worker_does_not_require_credentials_in_ui_mode(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    client = TestClient(app)
    initial = client.get("/settings/dispatch?mode=ui")
    assert initial.status_code == 200
    payload = initial.json()

    payload["workers"] = [
        {
            "source_name": "",
            "name": "disabled_codex",
            "enabled": False,
            "type": "codex",
            "task_types": ["reason"],
            "max_running": 1,
            "priority": 0,
            "provider_id": "",
            "provider_supported": True,
            "model": "",
            "base_url": "",
            "auth_token": "",
            "has_auth_token": False,
            "provider_api": "",
            "context_window": None,
            "mcp_server_ids": [],
            "skill_ids": [],
            "mcp_supported": True,
            "skill_supported": False,
        }
    ]
    payload["providers"] = []
    payload["mcp_servers"] = []
    payload["skills"] = []
    payload["worker_bindings"] = []

    saved = client.put("/settings/dispatch", json=payload)
    assert saved.status_code == 200, saved.text
    compiled = (tmp_path / "datas" / "cairn" / "dispatch_ui.yaml").read_text(encoding="utf-8")
    assert "name: disabled_codex" in compiled
    assert "enabled: false" in compiled


def test_app_enabled_skill_is_injected_without_worker_binding(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    client = TestClient(app)
    response = client.get("/settings/dispatch?mode=ui")
    assert response.status_code == 200
    payload = response.json()
    payload["skills"] = [
        {
            "id": "redis-protocol",
            "name": "Redis Protocol",
            "enabled": True,
            "path": "/tmp/redis-protocol",
            "description": "Redis SSRF skill",
            "enabled_claude": False,
            "enabled_codex": True,
        }
    ]
    payload["worker_bindings"] = [
        {
            "worker_name": payload["workers"][0]["name"],
            "mcp_server_ids": [],
            "skill_ids": [],
        }
    ]

    saved = client.put("/settings/dispatch", json=payload)
    assert saved.status_code == 200, saved.text

    compiled = (tmp_path / "datas" / "cairn" / "dispatch_ui.yaml").read_text(encoding="utf-8")
    assert "CAIRN_SKILLS:" in compiled
    assert "redis-protocol" in compiled


def test_ui_settings_hides_runtime_injected_env_from_editable_extra_env(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    client = TestClient(app)
    initial = client.get("/settings/dispatch?mode=ui")
    assert initial.status_code == 200
    payload = initial.json()

    payload["workers"][0]["extra_env"] = {
        "CAIRN_PROVIDER_SPEC": '{"id":"runtime"}',
        "CAIRN_MCP_SERVERS": "[]",
        "CAIRN_SKILLS": "[]",
        "CUSTOM_FLAG": "kept",
    }
    payload["providers"][0]["extra_env"] = {
        "CAIRN_PROVIDER_SPEC": '{"id":"nested"}',
        "CUSTOM_PROVIDER_ENV": "kept",
    }

    saved = client.put("/settings/dispatch", json=payload)
    assert saved.status_code == 200, saved.text
    saved_data = saved.json()
    assert saved_data["workers"][0]["extra_env"] == {"CUSTOM_PROVIDER_ENV": "kept"}
    assert saved_data["providers"][0]["extra_env"] == {"CUSTOM_PROVIDER_ENV": "kept"}

    compiled = (tmp_path / "datas" / "cairn" / "dispatch_ui.yaml").read_text(encoding="utf-8")
    assert "CUSTOM_PROVIDER_ENV: kept" in compiled
    assert "CAIRN_MCP_SERVERS: '[]'" not in compiled
    assert "CAIRN_SKILLS: '[]'" not in compiled
    assert '"id":"nested"' not in compiled


def test_discover_skills_prefers_ui_registry_root(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    registry_skill = tmp_path / "datas" / "cairn" / "registry" / "skills" / "web-ssrf"
    registry_skill.mkdir(parents=True, exist_ok=True)
    (registry_skill / "SKILL.md").write_text("# Web SSRF\n\nRegistry managed skill.\n", encoding="utf-8")

    client = TestClient(app)
    payload = client.get("/settings/dispatch/skills/discover?mode=ui")
    assert payload.status_code == 200
    data = payload.json()
    registry_items = [item for item in data if item["source"] == "registry" and item["id"] == "web-ssrf"]
    assert len(registry_items) == 1
    assert registry_items[0]["path"].endswith("datas/cairn/registry/skills/web-ssrf")


def test_discover_skills_syncs_repo_skill_into_registry(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    repo_skill = tmp_path / "skills" / "web-ssrf"
    repo_skill.mkdir(parents=True, exist_ok=True)
    (repo_skill / "SKILL.md").write_text(
        "---\nname: web-ssrf\n---\n# Web SSRF\n\nFresh repo skill.\n",
        encoding="utf-8",
    )

    registry_skill = tmp_path / "datas" / "cairn" / "registry" / "skills" / "web-ssrf"
    registry_skill.mkdir(parents=True, exist_ok=True)
    (registry_skill / "SKILL.md").write_text("# Web SSRF\n\nStale registry skill.\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    client = TestClient(app)
    payload = client.get("/settings/dispatch/skills/discover?mode=ui")
    assert payload.status_code == 200
    data = payload.json()

    registry_items = [item for item in data if item["id"] == "web-ssrf"]
    assert len(registry_items) == 1
    assert registry_items[0]["source"] == "registry"
    assert registry_items[0]["path"].endswith("datas/cairn/registry/skills/web-ssrf")

    synced = (registry_skill / "SKILL.md").read_text(encoding="utf-8")
    assert "Fresh repo skill." in synced
    assert "Stale registry skill." not in synced


def test_worker_healthcheck_endpoint_returns_mock_result(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cairn.db"
    db._db_path = None
    db.configure(db_path)

    dispatch_path = tmp_path / "dispatch.yaml"
    _write_dispatch(dispatch_path)

    monkeypatch.setenv("CAIRN_DISPATCH_CONFIG", str(dispatch_path))
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(tmp_path / "datas" / "cairn" / "dispatch_ui.yaml"))
    monkeypatch.setenv("CAIRN_DISPATCH_SETTINGS_MODE", "ui")

    client = TestClient(app)
    response = client.post(
        "/settings/dispatch/workers/healthcheck",
        json={
            "mode": "ui",
            "runtime": {
                "interval": 3,
                "max_workers": 1,
                "max_running_projects": 1,
                "max_project_workers": 1,
                "healthcheck_timeout": 5,
                "prompt_group": "default",
            },
            "worker": {
                "source_name": "",
                "name": "mock_probe",
                "enabled": True,
                "type": "mock",
                "task_types": ["reason"],
                "max_running": 1,
                "priority": 0,
                "provider_id": "",
                "provider_supported": False,
                "model": "",
                "base_url": "",
                "auth_token": "",
                "has_auth_token": False,
                "provider_api": "",
                "context_window": None,
                "extra_env": {},
                "mcp_server_ids": [],
                "skill_ids": [],
                "mcp_supported": False,
                "skill_supported": False,
            },
            "providers": [],
            "mcp_servers": [],
            "skills": [],
            "worker_bindings": [],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["worker_name"] == "mock_probe"
    assert data["worker_type"] == "mock"
    assert data["ok"] is True
