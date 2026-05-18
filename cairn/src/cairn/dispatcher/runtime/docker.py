from __future__ import annotations

import io
import logging
from pathlib import Path, PurePosixPath
import re
import tarfile
import threading
import uuid

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container

from cairn.dispatcher.config import ContainerConfig, ExecutionConfig
from cairn.dispatcher.runtime.docker_process import DockerManagedProcess

LOG = logging.getLogger(__name__)


class DockerRuntimeManager:
    _PREFIX = "cairn-dispatch-"
    _STARTUP_PREFIX = "cairn-startup-healthcheck-"
    _CONTAINER_WORKSPACE_ROOT = PurePosixPath("/tmp/cairn-workspaces")

    def __init__(self, execution: ExecutionConfig, container: ContainerConfig):
        self._execution = execution
        self._config = container
        self._root = execution.work_dir.resolve()
        self._observer_root = self._root / "observer"
        self._client = docker.from_env()
        self._session_home = PurePosixPath(container.session_home)
        self._ensure_running_locks: dict[str, threading.Lock] = {}
        self._ensure_running_locks_guard = threading.Lock()
        self._startup_containers: list[str] = []

    def close(self) -> None:
        for name in self._startup_containers:
            self.cleanup_orphan(name)
        self._client.close()

    def workspace_name(self, project_id: str) -> str:
        return _sanitize_name(project_id)

    def container_name(self, project_id: str) -> str:
        return f"{self._PREFIX}{self.workspace_name(project_id)}"

    def ensure_running(self, project_id: str) -> str:
        name = self.container_name(project_id)
        with self._ensure_running_lock(name):
            return self._ensure_running_locked(project_id, name)

    def ensure_startup_workspace(self) -> str:
        name = f"startup:{uuid.uuid4().hex[:12]}"
        container_name = f"{self._STARTUP_PREFIX}{uuid.uuid4().hex[:12]}"
        LOG.debug("creating startup healthcheck container container=%s image=%s", container_name, self._config.image)
        try:
            self._client.containers.run(
                self._config.image,
                ["sleep", "infinity"],
                detach=True,
                name=container_name,
                network_mode=self._config.network_mode,
                cap_add=self._config.cap_add or None,
                volumes=self._session_volumes(),
            )
        except DockerException as exc:
            raise RuntimeError(f"failed to create startup container {container_name}: {exc}") from exc
        self._startup_containers.append(container_name)
        return f"{name}:{container_name}"

    def build_exec_process(
        self,
        workspace_name: str,
        env: dict[str, str],
        command: list[str],
        timeout_seconds: int | None = None,
    ) -> DockerManagedProcess:
        container = self._require_workspace_container(workspace_name)
        self._ensure_container_dir(container, self.workspace_path(workspace_name))
        env = self._with_session_env(env)
        argv: list[str] = []
        if timeout_seconds is not None:
            argv.extend(["timeout", "-k", "5s", f"{timeout_seconds}s"])
        argv.extend(command)
        return DockerManagedProcess(container, argv, env, workdir=str(self.workspace_path(workspace_name)))

    def workspace_path(self, workspace_name: str) -> PurePosixPath:
        return self._CONTAINER_WORKSPACE_ROOT / _sanitize_name(workspace_name.replace(":", "-"))

    def write_text_file(self, workspace_name: str, relative_path: str, content: str) -> str:
        container = self._require_workspace_container(workspace_name)
        target = self.workspace_path(workspace_name) / PurePosixPath(relative_path)
        self._put_text_file(container, target, content)
        return str(target)

    def copy_directory(self, workspace_name: str, source_dir: str, relative_path: str) -> str:
        container = self._require_workspace_container(workspace_name)
        source = Path(source_dir).resolve()
        if not source.is_dir():
            raise ValueError(f"source directory does not exist: {source_dir}")
        target = self.workspace_path(workspace_name) / PurePosixPath(relative_path)
        self._put_directory(container, target, source)
        return str(target)

    def link_or_copy_directory(self, workspace_name: str, relative_path: str, target_path: str) -> str:
        container = self._require_workspace_container(workspace_name)
        link_path = self.workspace_path(workspace_name) / PurePosixPath(relative_path)
        target = PurePosixPath(target_path)
        self._ensure_container_dir(container, link_path.parent)
        self._ensure_container_dir(container, target)
        command = ["sh", "-lc", f"rm -rf {_sh_quote(str(link_path))} && ln -s {_sh_quote(str(target))} {_sh_quote(str(link_path))}"]
        try:
            result = container.exec_run(command, stdout=False, stderr=True)
        except DockerException as exc:
            raise RuntimeError(
                f"failed to link {link_path} to {target} in container {container.name}: {exc}"
            ) from exc
        exit_code = result.exit_code if hasattr(result, "exit_code") else None
        if exit_code not in (None, 0):
            raise RuntimeError(f"failed to link {link_path} to {target} in container {container.name}: exit {exit_code}")
        return str(link_path)

    def write_observer_text_file(self, relative_path: str, content: str) -> str:
        target = self._observer_root / relative_path
        resolved = target.resolve()
        observer_root = self._observer_root.resolve()
        if observer_root != resolved and observer_root not in resolved.parents:
            raise ValueError(f"refusing to write outside observer directory: {relative_path}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return str(resolved)

    def cleanup_completed(self, project_id: str) -> bool:
        name = self.container_name(project_id)
        state = self.inspect_state(name)
        if state is None:
            return True
        container = self._require_container(name)
        if self._config.completed_action == "remove":
            LOG.info("removing completed project container project=%s container=%s", project_id, name)
            try:
                container.remove(force=True)
            except NotFound:
                return True
            except DockerException as exc:
                LOG.warning("failed to remove container=%s error=%s", name, exc)
                return False
            return self.inspect_state(name) is None
        if state == "running":
            LOG.info("stopping completed project container project=%s container=%s", project_id, name)
            return self._stop_container(container, name)
        return True

    def cleanup_stopped(self, project_id: str) -> bool:
        name = self.container_name(project_id)
        state = self.inspect_state(name)
        if state != "running":
            return True
        LOG.info("stopping stopped project container project=%s container=%s", project_id, name)
        return self._stop_container(self._require_container(name), name)

    def cleanup_orphan(self, name: str) -> bool:
        state = self.inspect_state(name)
        if state is None:
            return True
        LOG.info("removing orphan project container container=%s state=%s", name, state)
        container = self._require_container(name)
        try:
            container.remove(force=True)
        except NotFound:
            return True
        except DockerException as exc:
            LOG.warning("failed to remove orphan container=%s error=%s", name, exc)
            return False
        return self.inspect_state(name) is None

    def managed_container_names(self) -> list[str]:
        try:
            containers = self._client.containers.list(all=True)
        except DockerException as exc:
            LOG.warning("failed to list managed containers error=%s", exc)
            return []
        return sorted(container.name for container in containers if container.name.startswith(self._PREFIX))

    def inspect_state(self, name: str) -> str | None:
        container = self._get_container(name)
        if container is None:
            return None
        try:
            container.reload()
        except DockerException as exc:
            raise RuntimeError(f"failed to inspect container {name}: {exc}") from exc
        state = container.attrs.get("State", {}).get("Status")
        return str(state) if state else None

    def _ensure_running_locked(self, project_id: str, name: str) -> str:
        state = self.inspect_state(name)
        if state == "running":
            LOG.debug("container already running project=%s container=%s", project_id, name)
            return name
        if state is not None:
            LOG.info("starting existing container project=%s container=%s state=%s", project_id, name, state)
            self._start_existing(name)
            return name
        LOG.info("creating container project=%s container=%s image=%s", project_id, name, self._config.image)
        try:
            self._client.containers.run(
                self._config.image,
                ["sleep", "infinity"],
                detach=True,
                name=name,
                network_mode=self._config.network_mode,
                cap_add=self._config.cap_add or None,
                volumes=self._session_volumes(),
            )
            LOG.info("created container project=%s container=%s", project_id, name)
            return name
        except APIError as exc:
            if not self._is_name_conflict(exc):
                raise RuntimeError(f"failed to create container {name}: {exc}") from exc
        LOG.info("container name conflict, reusing existing container project=%s container=%s", project_id, name)
        state = self.inspect_state(name)
        if state == "running":
            return name
        if state is not None:
            self._start_existing(name)
            return name
        raise RuntimeError(f"failed to create container {name}")

    def _ensure_running_lock(self, name: str) -> threading.Lock:
        with self._ensure_running_locks_guard:
            lock = self._ensure_running_locks.get(name)
            if lock is None:
                lock = threading.Lock()
                self._ensure_running_locks[name] = lock
            return lock

    def _require_workspace_container(self, workspace_name: str) -> Container:
        if workspace_name.startswith("startup:"):
            container_name = workspace_name.split(":")[-1]
            return self._require_container(container_name)
        return self._require_container(workspace_name)

    def _get_container(self, name: str) -> Container | None:
        try:
            return self._client.containers.get(name)
        except NotFound:
            return None
        except DockerException as exc:
            raise RuntimeError(f"failed to get container {name}: {exc}") from exc

    def _require_container(self, name: str) -> Container:
        container = self._get_container(name)
        if container is None:
            raise RuntimeError(f"container {name} does not exist")
        return container

    def _start_existing(self, name: str) -> None:
        container = self._require_container(name)
        try:
            container.start()
        except DockerException as exc:
            raise RuntimeError(f"failed to start container {name}: {exc}") from exc

    def _with_session_env(self, env: dict[str, str]) -> dict[str, str]:
        merged = dict(env)
        merged.setdefault("HOME", str(self._session_home))
        merged.setdefault("CLAUDE_PROJECTS_DIR", str(self._session_home / ".claude" / "projects"))
        merged.setdefault("CODEX_SESSIONS_DIR", str(self._session_home / ".codex" / "sessions"))
        merged.setdefault("PI_DIR", str(self._session_home / ".pi" / "agent" / "sessions"))
        return merged

    def _session_volumes(self) -> dict[str, dict[str, str]]:
        return {
            self._config.session_volume: {
                "bind": str(self._session_home),
                "mode": "rw",
            }
        }

    def _stop_container(self, container: Container, name: str) -> bool:
        try:
            container.stop(timeout=1)
        except NotFound:
            return True
        except DockerException as exc:
            LOG.warning("failed to stop container=%s error=%s", name, exc)
            return False
        return self.inspect_state(name) != "running"

    def _put_text_file(self, container: Container, path: PurePosixPath, content: str) -> None:
        self._ensure_container_dir(container, path.parent)
        archive_path, archive = _text_file_archive(path, content)
        try:
            ok = container.put_archive(archive_path, archive)
        except DockerException as exc:
            raise RuntimeError(f"failed to write file {path} in container {container.name}: {exc}") from exc
        if not ok:
            raise RuntimeError(f"failed to write file {path} in container {container.name}")

    def _ensure_container_dir(self, container: Container, path: PurePosixPath) -> None:
        try:
            result = container.exec_run(["mkdir", "-p", str(path)], stdout=False, stderr=False)
        except DockerException as exc:
            raise RuntimeError(f"failed to create directory {path} in container {container.name}: {exc}") from exc
        exit_code = result.exit_code if hasattr(result, "exit_code") else None
        if exit_code not in (None, 0):
            raise RuntimeError(f"failed to create directory {path} in container {container.name}: exit {exit_code}")

    def _put_directory(self, container: Container, path: PurePosixPath, source: Path) -> None:
        self._ensure_container_dir(container, path.parent)
        archive_path, archive = _directory_archive(path, source)
        try:
            ok = container.put_archive(archive_path, archive)
        except DockerException as exc:
            raise RuntimeError(f"failed to copy directory {source} to {path} in container {container.name}: {exc}") from exc
        if not ok:
            raise RuntimeError(f"failed to copy directory {source} to {path} in container {container.name}")

    @staticmethod
    def _is_name_conflict(exc: APIError) -> bool:
        explanation = getattr(exc, "explanation", "")
        return "Conflict" in str(exc) or "already in use" in str(explanation)


def _text_file_archive(path: PurePosixPath, content: str) -> tuple[str, bytes]:
    normalized = PurePosixPath("/") / path.relative_to("/") if path.is_absolute() else PurePosixPath("/") / path
    parent = normalized.parent
    filename = normalized.name
    data = content.encode("utf-8")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        info = tarfile.TarInfo(filename)
        info.size = len(data)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))
    return str(parent), buffer.getvalue()


def _directory_archive(path: PurePosixPath, source: Path) -> tuple[str, bytes]:
    normalized = PurePosixPath("/") / path.relative_to("/") if path.is_absolute() else PurePosixPath("/") / path
    parent = normalized.parent
    dirname = normalized.name
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for item in sorted(source.rglob("*")):
            rel = item.relative_to(source)
            arcname = PurePosixPath(dirname) / PurePosixPath(rel.as_posix())
            info_name = str(arcname)
            if item.is_dir():
                info = tarfile.TarInfo(info_name)
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
                continue
            data = item.read_bytes()
            info = tarfile.TarInfo(info_name)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return str(parent), buffer.getvalue()


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _sanitize_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return text or "project"
