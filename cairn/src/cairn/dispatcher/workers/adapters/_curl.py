from __future__ import annotations

import shlex
import sys
from dataclasses import dataclass


_VERBOSE_CURL_SCRIPT = """
import subprocess
import sys
import tempfile

url = sys.argv[1]
payload = sys.argv[2]
args = sys.argv[3:]

with tempfile.NamedTemporaryFile(delete=False) as body_file:
    body_path = body_file.name

command = ["curl", "-sS", "-o", body_path, "-w", "%{http_code}", url, *args, "-d", payload]
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
http_status = result.stdout.strip()
print(f"http_status={http_status}")
try:
    with open(body_path, "r", encoding="utf-8", errors="replace") as handle:
        body = handle.read()
except OSError:
    body = ""
if body:
    print(body, end="" if body.endswith("\\n") else "\\n")
if result.stderr:
    print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\\n") else "\\n")
if result.returncode != 0:
    raise SystemExit(result.returncode)
raise SystemExit(0 if http_status.startswith("2") else 1)
""".strip()


def build_verbose_curl_healthcheck(url: str, *, headers: list[str], payload: str) -> list[str]:
    return [sys.executable, "-c", _VERBOSE_CURL_SCRIPT, url, payload, *headers]


@dataclass(frozen=True, slots=True)
class ShellArgument:
    text: str
    expand_env: bool = False


def expand_env(text: str) -> ShellArgument:
    return ShellArgument(text=text, expand_env=True)


def render_curl_command(url: str, *, headers: list[str | ShellArgument], payload: str) -> str:
    parts = ["curl", "-sS", url, *headers, "-d", payload]
    return " ".join(_render_shell_argument(part) for part in parts)


def _render_shell_argument(part: str | ShellArgument) -> str:
    if isinstance(part, ShellArgument):
        if part.expand_env:
            return _double_quote_with_env_expansion(part.text)
        return shlex.quote(part.text)
    return shlex.quote(part)


def _double_quote_with_env_expansion(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
