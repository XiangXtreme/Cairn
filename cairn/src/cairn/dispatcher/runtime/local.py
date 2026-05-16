from __future__ import annotations

from pathlib import Path
import re

from cairn.dispatcher.config import ExecutionConfig
from cairn.dispatcher.runtime.process import ManagedProcess


class LocalRuntimeManager:
    def __init__(self, config: ExecutionConfig):
        self._root = config.work_dir.resolve()
        self._projects_root = self._root / "projects"
        self._startup_root = self._root / "startup-healthchecks"

    def close(self) -> None:
        return None

    def workspace_name(self, project_id: str) -> str:
        return _sanitize_name(project_id)

    def ensure_running(self, project_id: str) -> str:
        workspace = self._project_workspace(project_id)
        workspace.mkdir(parents=True, exist_ok=True)
        return self.workspace_name(project_id)

    def ensure_startup_workspace(self) -> str:
        name = "startup"
        (self._startup_root / name).mkdir(parents=True, exist_ok=True)
        return f"startup:{name}"

    def build_exec_process(
        self,
        workspace_name: str,
        env: dict[str, str],
        command: list[str],
        timeout_seconds: int | None = None,
    ) -> ManagedProcess:
        return ManagedProcess(command, env, self._workspace_path(workspace_name))

    def workspace_path(self, workspace_name: str) -> Path:
        return self._workspace_path(workspace_name).resolve()

    def write_text_file(self, workspace_name: str, relative_path: str, content: str) -> str:
        target = self._workspace_path(workspace_name) / relative_path
        resolved = target.resolve()
        workspace = self._workspace_path(workspace_name).resolve()
        if workspace != resolved and workspace not in resolved.parents:
            raise ValueError(f"refusing to write outside workspace: {relative_path}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return str(resolved)

    def write_observer_text_file(self, relative_path: str, content: str) -> str:
        target = self._root / "observer" / relative_path
        resolved = target.resolve()
        observer_root = (self._root / "observer").resolve()
        if observer_root != resolved and observer_root not in resolved.parents:
            raise ValueError(f"refusing to write outside observer directory: {relative_path}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return str(resolved)

    def cleanup_completed(self, project_id: str) -> bool:
        return True

    def cleanup_stopped(self, project_id: str) -> bool:
        return True

    def _project_workspace(self, project_id: str) -> Path:
        return self._projects_root / self.workspace_name(project_id)

    def _workspace_path(self, workspace_name: str) -> Path:
        if workspace_name.startswith("startup:"):
            return self._startup_root / workspace_name.partition(":")[2]
        return self._projects_root / workspace_name


def _sanitize_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return text or "project"
