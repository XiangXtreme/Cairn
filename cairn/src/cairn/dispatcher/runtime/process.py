from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import signal
import subprocess
import threading

LOG = logging.getLogger(__name__)
PROCESS_KILL_JOIN_TIMEOUT_SECONDS = 5.0


@dataclass(slots=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False
    cancel_reason: str | None = None


class ManagedProcess:
    def __init__(self, command: list[str], env: dict[str, str], cwd: Path):
        self.command = command
        self.env = env
        self.cwd = cwd
        self._process: subprocess.Popen[str] | None = None
        self._timed_out = False
        self._cancel_reason: str | None = None
        self._stdout = ""
        self._stderr = ""
        self._lock = threading.Lock()

    def start(self) -> None:
        merged_env = os.environ.copy()
        merged_env.update(self.env)
        self.cwd.mkdir(parents=True, exist_ok=True)
        creationflags = 0
        start_new_session = False
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            start_new_session = True
        self._process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            env=merged_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            start_new_session=start_new_session,
        )

    def communicate(self, timeout: float | None) -> ProcessResult:
        assert self._process is not None
        try:
            stdout, stderr = self._process.communicate(timeout=timeout)
            self._stdout = stdout
            self._stderr = stderr
        except subprocess.TimeoutExpired:
            self._timed_out = True
            self.kill()
            try:
                stdout, stderr = self._process.communicate(timeout=PROCESS_KILL_JOIN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "process did not exit after kill"
            self._stdout = stdout or ""
            self._stderr = stderr or ""
        return ProcessResult(
            returncode=self._process.returncode if self._process.returncode is not None else 1,
            stdout=self._stdout,
            stderr=self._stderr,
            timed_out=self._timed_out,
            cancelled=self._cancel_reason is not None,
            cancel_reason=self._cancel_reason,
        )

    def kill(self) -> None:
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        if os.name == "nt":
            self._kill_windows_process_tree(process.pid)
            return
        self._kill_posix_process_tree(process.pid)

    def cancel(self, reason: str) -> None:
        if self._cancel_reason is None:
            self._cancel_reason = reason
        self.kill()

    @staticmethod
    def _kill_windows_process_tree(pid: int) -> None:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode not in (0, 128):
            LOG.warning("taskkill failed pid=%s returncode=%s", pid, result.returncode)

    @staticmethod
    def _kill_posix_process_tree(pid: int) -> None:
        with suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGTERM)
        with suppress(Exception):
            _, _ = os.waitpid(pid, os.WNOHANG)
        with suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGKILL)
