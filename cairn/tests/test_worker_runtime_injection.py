from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from cairn.dispatcher.config import WorkerConfig
from cairn.dispatcher.runtime.local import LocalRuntimeManager
from cairn.dispatcher.config import ExecutionConfig
from cairn.dispatcher.workers.adapters.codex import CodexDriver
from cairn.dispatcher.workers.runtime_injection import prepare_worker_runtime_files


class DockerLikeRuntime(LocalRuntimeManager):
    def __init__(self, config: ExecutionConfig):
        super().__init__(config)
        self.shared_root = self._root / "shared-session-home"

    def workspace_path(self, workspace_name: str) -> PurePosixPath:
        return PurePosixPath("/tmp/cairn-workspaces") / workspace_name

    def link_or_copy_directory(self, workspace_name: str, relative_path: str, target_path: str) -> str:
        mapped = self.shared_root / target_path.lstrip("/")
        return super().link_or_copy_directory(workspace_name, relative_path, str(mapped))


def test_codex_runtime_injection_creates_dedicated_codex_home(tmp_path: Path) -> None:
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
            "CODEX_SESSIONS_DIR": str(tmp_path / "shared-codex-sessions"),
            "CAIRN_PROVIDER_SPEC": (
                '{"id":"codex_main_provider","name":"Codex Main","kind":"codex",'
                '"model":"gpt-5.5","base_url":"https://ai.example.test/v1","extra_env":{}}'
            ),
            "CAIRN_MCP_SERVERS": (
                '[{"id":"context7","name":"Context7","transport":"stdio","command":"npx",'
                '"args":["-y","@upstash/context7-mcp"],"env":{"FOO":"bar"}}]'
            ),
        },
    )
    runtime = LocalRuntimeManager(ExecutionConfig(backend="local", work_dir=tmp_path))
    workspace_name = runtime.ensure_running("proj_test")

    env_updates = prepare_worker_runtime_files(runtime, workspace_name, worker)

    codex_home = Path(env_updates["CODEX_HOME"])
    config_path = codex_home / "config.toml"
    assert config_path.exists()
    config_text = config_path.read_text(encoding="utf-8")
    assert 'model_provider = "codex_main_provider"' in config_text
    assert '[model_providers."codex_main_provider"]' in config_text
    assert 'env_key = "OPENAI_API_KEY"' in config_text
    assert '[mcp_servers."context7"]' in config_text
    assert 'command = "npx"' in config_text
    assert 'args = ["-y", "@upstash/context7-mcp"]' in config_text
    assert env_updates["HOME"] == env_updates["CODEX_HOME"]
    assert (codex_home / "sessions").is_symlink()
    assert (codex_home / "sessions").resolve() == tmp_path / "shared-codex-sessions"


def test_codex_driver_uses_runtime_config_without_inline_provider_overrides() -> None:
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
        },
    )
    driver = CodexDriver()
    result = driver.build_execute(worker, "hello", None)

    assert "--ignore-user-config" not in result.argv
    assert "--dangerously-bypass-approvals-and-sandbox" in result.argv
    assert 'model_provider="cairn"' not in result.argv
    assert not any("model_providers.cairn" in item for item in result.argv)


def test_claudecode_runtime_injection_creates_claude_home_files(tmp_path: Path) -> None:
    worker = WorkerConfig(
        name="claude_main",
        type="claudecode",
        enabled=True,
        task_types=["reason"],
        max_running=1,
        priority=0,
        env={
            "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
            "ANTHROPIC_BASE_URL": "https://anthropic.example.test",
            "ANTHROPIC_AUTH_TOKEN": "sk-test",
            "CAIRN_MCP_SERVERS": (
                '[{"id":"fetch","name":"Fetch","transport":"stdio","command":"uvx",'
                '"args":["mcp-fetch"],"env":{"HTTP_PROXY":"http://127.0.0.1:7890"}}]'
            ),
        },
    )
    runtime = LocalRuntimeManager(ExecutionConfig(backend="local", work_dir=tmp_path))
    workspace_name = runtime.ensure_running("proj_claude")

    env_updates = prepare_worker_runtime_files(runtime, workspace_name, worker)

    claude_home = Path(env_updates["HOME"])
    claude_json = claude_home / ".claude.json"
    settings_json = claude_home / ".claude" / "settings.json"
    assert claude_json.exists()
    assert settings_json.exists()
    claude_text = claude_json.read_text(encoding="utf-8")
    assert '"mcpServers"' in claude_text
    assert '"fetch"' in claude_text
    assert '"command": "uvx"' in claude_text
    assert env_updates["CLAUDE_CONFIG_DIR"].endswith("/.cairn/claude-home/claude_main")
    assert not (claude_home / "projects").exists()
    assert not (claude_home / "sessions").exists()
    assert not (claude_home / "backups").exists()


def test_runtime_injection_materializes_project_skill_directories(tmp_path: Path) -> None:
    skill_dir = tmp_path / "project-skills" / "web"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Web Skill\n\nContainer skill.\n", encoding="utf-8")

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
                        "id": "web",
                        "name": "Web Skill",
                        "path": str(skill_dir),
                        "description": "Container skill",
                    }
                ]
            ),
        },
    )
    runtime = LocalRuntimeManager(ExecutionConfig(backend="local", work_dir=tmp_path / "runtime"))
    workspace_name = runtime.ensure_running("proj_skill")

    env_updates = prepare_worker_runtime_files(runtime, workspace_name, worker)

    skill_paths = env_updates["CAIRN_SKILL_PATHS"].split(":")
    assert len(skill_paths) == 1
    runtime_skill_dir = Path(skill_paths[0])
    assert runtime_skill_dir.exists()
    assert (runtime_skill_dir / "SKILL.md").exists()

    codex_home = Path(env_updates["CODEX_HOME"])
    codex_skill_dir = codex_home / "skills" / "web"
    agents_skill_dir = codex_home / ".agents" / "skills" / "web"
    assert codex_skill_dir.exists()
    assert (codex_skill_dir / "SKILL.md").exists()
    assert agents_skill_dir.exists()
    assert (agents_skill_dir / "SKILL.md").exists()


def test_runtime_injection_remaps_ui_registry_skill_paths_for_container_mounts(tmp_path: Path, monkeypatch) -> None:
    mounted_data_root = tmp_path / "mounted-cairn-data"
    mounted_skill_dir = mounted_data_root / "registry" / "skills" / "web-ai"
    mounted_skill_dir.mkdir(parents=True)
    (mounted_skill_dir / "SKILL.md").write_text("# Web AI\n\nMounted skill.\n", encoding="utf-8")
    monkeypatch.setenv("CAIRN_UI_DISPATCH_CONFIG", str(mounted_data_root / "dispatch_ui.yaml"))

    host_only_path = "/host-only/Cairn/datas/cairn/registry/skills/web-ai"
    assert not Path(host_only_path).is_dir()
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
                        "id": "web-ai",
                        "name": "Web AI",
                        "path": host_only_path,
                        "description": "Mounted registry skill",
                    }
                ]
            ),
        },
    )
    runtime = LocalRuntimeManager(ExecutionConfig(backend="local", work_dir=tmp_path / "runtime-remap"))
    workspace_name = runtime.ensure_running("proj_skill_remap")

    env_updates = prepare_worker_runtime_files(runtime, workspace_name, worker)

    runtime_skill_dir = Path(env_updates["CAIRN_SKILL_PATHS"])
    assert runtime_skill_dir.exists()
    assert (runtime_skill_dir / "SKILL.md").read_text(encoding="utf-8").startswith("# Web AI")

    codex_home = Path(env_updates["CODEX_HOME"])
    assert (codex_home / "skills" / "web-ai" / "SKILL.md").exists()
    assert (codex_home / ".agents" / "skills" / "web-ai" / "SKILL.md").exists()


def test_claude_runtime_injection_materializes_skill_directories(tmp_path: Path) -> None:
    skill_dir = tmp_path / "project-skills" / "redirect-bypass"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Redirect Bypass\n\nClaude can use this.\n", encoding="utf-8")

    worker = WorkerConfig(
        name="claude_main",
        type="claudecode",
        enabled=True,
        task_types=["reason"],
        max_running=1,
        priority=0,
        env={
            "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
            "ANTHROPIC_BASE_URL": "https://anthropic.example.test",
            "ANTHROPIC_AUTH_TOKEN": "sk-test",
            "CAIRN_SKILLS": json.dumps(
                [
                    {
                        "id": "redirect-bypass",
                        "name": "Redirect Bypass",
                        "path": str(skill_dir),
                        "description": "Container skill",
                    }
                ]
            ),
        },
    )
    runtime = LocalRuntimeManager(ExecutionConfig(backend="local", work_dir=tmp_path / "runtime-claude"))
    workspace_name = runtime.ensure_running("proj_skill_claude")

    env_updates = prepare_worker_runtime_files(runtime, workspace_name, worker)

    claude_home = Path(env_updates["HOME"])
    claude_skill_dir = claude_home / ".claude" / "skills" / "redirect-bypass"
    agents_skill_dir = claude_home / ".agents" / "skills" / "redirect-bypass"
    assert claude_skill_dir.exists()
    assert (claude_skill_dir / "SKILL.md").exists()
    assert agents_skill_dir.exists()
    assert (agents_skill_dir / "SKILL.md").exists()


def test_claudecode_runtime_injection_links_shared_session_dirs_for_docker_runtime(tmp_path: Path) -> None:
    worker = WorkerConfig(
        name="claude_main",
        type="claudecode",
        enabled=True,
        task_types=["reason"],
        max_running=1,
        priority=0,
        env={
            "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
            "ANTHROPIC_BASE_URL": "https://anthropic.example.test",
            "ANTHROPIC_AUTH_TOKEN": "sk-test",
        },
    )
    runtime = DockerLikeRuntime(ExecutionConfig(backend="local", work_dir=tmp_path / "runtime-docker-like"))
    workspace_name = runtime.ensure_running("proj_claude_shared")

    env_updates = prepare_worker_runtime_files(runtime, workspace_name, worker)

    claude_home = tmp_path / "runtime-docker-like/projects/proj_claude_shared/.cairn/claude-home/claude_main"
    assert env_updates["HOME"] == "/tmp/cairn-workspaces/proj_claude_shared/.cairn/claude-home/claude_main"
    assert (claude_home / "projects").is_symlink()
    assert (claude_home / "projects").resolve() == runtime.shared_root / "cairn-observer-sessions/.claude/projects"
    assert (claude_home / "sessions").is_symlink()
    assert (claude_home / "sessions").resolve() == runtime.shared_root / "cairn-observer-sessions/.claude/sessions"
    assert (claude_home / "backups").is_symlink()
    assert (claude_home / "backups").resolve() == runtime.shared_root / "cairn-observer-sessions/.claude/backups"
