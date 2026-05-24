#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/dev-rebuild.sh <command>

Unified rebuild/restart helper for the Cairn development stack.

Commands:
  cairn     Rebuild cairn-server and cairn-dispatcher images, then recreate them
  observer  Rebuild the local agentsview binary with FTS5, then restart cairn-observer
  all       Rebuild everything above
  check     Show service status and probe the main HTTP endpoints
  runtime   Inspect generated worker runtime config artifacts under datas/cairn-runtime
  help      Show this help

Examples:
  ./scripts/dev-rebuild.sh cairn
  ./scripts/dev-rebuild.sh observer
  ./scripts/dev-rebuild.sh all
  ./scripts/dev-rebuild.sh check
  ./scripts/dev-rebuild.sh runtime
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
observer_dir="$repo_root/observer/agentsview"
prepare_observer_script="$repo_root/scripts/prepare-cairn-observer.sh"

cd "$repo_root"

ensure_worker_volume() {
  if ! docker volume inspect cairn-worker-sessions >/dev/null 2>&1; then
    log "Creating missing Docker volume: cairn-worker-sessions"
    docker volume create cairn-worker-sessions >/dev/null
  fi
}

rebuild_cairn() {
  ensure_worker_volume
  log "Building cairn-server and cairn-dispatcher images"
  docker compose build cairn-server cairn-dispatcher

  log "Recreating cairn-server and cairn-dispatcher"
  docker compose up -d --force-recreate cairn-server cairn-dispatcher
}

rebuild_observer() {
  ensure_worker_volume

  if [[ ! -d "$observer_dir" ]]; then
    echo "Observer source directory not found: $observer_dir" >&2
    exit 1
  fi

  log "Refreshing local Cairn observer bundle"
  "$prepare_observer_script" --force

  log "Starting/restarting cairn-observer"
  docker compose up -d cairn-observer
  docker compose restart cairn-observer

  log "Checking cairn-observer on 8081"
  python3 - <<'PY'
import socket
import sys
for _ in range(20):
    try:
        with socket.create_connection(("127.0.0.1", 8081), timeout=1):
            print("[OK] cairn-observer is listening on 127.0.0.1:8081")
            sys.exit(0)
    except OSError:
        pass
    import time
    time.sleep(1)
print("[FAIL] cairn-observer did not become ready on 127.0.0.1:8081")
sys.exit(1)
PY
}

health_check() {
  log "Service status"
  docker ps --format 'table {{.Names}}\t{{.Status}}' | rg 'cairn-server|cairn-dispatcher|cairn-observer' || true

  log "HTTP checks"
  python3 - <<'PY'
import json
import urllib.request

checks = [
    ("Cairn UI", "http://127.0.0.1:8000/"),
    ("Projects API", "http://127.0.0.1:8000/projects"),
    ("AgentsView", "http://127.0.0.1:8081/"),
]

for name, url in checks:
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            body = resp.read(200).decode("utf-8", errors="replace")
            print(f"[OK] {name}: {url}")
            if url.endswith("/projects"):
                try:
                    data = json.loads(body)
                    print(f"     projects preview: {len(data)} item(s)")
                except Exception:
                    print(f"     preview: {body[:120]!r}")
    except Exception as exc:
        print(f"[FAIL] {name}: {url} -> {exc}")
PY

  cat <<'EOF'

URLs:
  Cairn:      http://127.0.0.1:8000
  AgentsView: http://127.0.0.1:8081
EOF
}

runtime_check() {
  log "Runtime artifact scan"
  python3 - <<'PY'
from pathlib import Path
import json

root = Path("datas/cairn-runtime/projects")
if not root.exists():
    print("[INFO] No runtime project directory yet:", root)
    raise SystemExit(0)

provider_files = sorted(root.glob("*/.cairn/providers/*.json"))
mcp_files = sorted(root.glob("*/.cairn/mcp/*.json"))
skill_files = sorted(root.glob("*/.cairn/skills/*.json"))
codex_configs = sorted(root.glob("*/.cairn/codex-home/*/config.toml"))
claude_configs = sorted(root.glob("*/.cairn/claude-home/*/.claude.json"))

print(f"providers: {len(provider_files)}")
print(f"mcp files: {len(mcp_files)}")
print(f"skill files: {len(skill_files)}")
print(f"codex homes: {len(codex_configs)}")
print(f"claude homes: {len(claude_configs)}")

def preview_json(path: Path):
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return f"invalid json: {exc}"
    if isinstance(payload, dict):
        keys = ", ".join(sorted(payload.keys())[:6])
        return f"dict keys: {keys}"
    if isinstance(payload, list):
        return f"list items: {len(payload)}"
    return type(payload).__name__

for label, items in [
    ("provider", provider_files[:3]),
    ("mcp", mcp_files[:3]),
    ("skill", skill_files[:3]),
]:
    for path in items:
        print(f" - {label}: {path} -> {preview_json(path)}")

for path in codex_configs[:3]:
    text = path.read_text(encoding="utf-8")
    has_mcp = "[mcp_servers." in text
    print(f" - codex: {path} -> mcp={has_mcp}")

for path in claude_configs[:3]:
    print(f" - claude: {path} -> {preview_json(path)}")
PY
}

command="${1:-help}"

case "$command" in
  cairn)
    rebuild_cairn
    health_check
    ;;
  observer)
    rebuild_observer
    health_check
    ;;
  all)
    rebuild_cairn
    rebuild_observer
    health_check
    ;;
  check)
    health_check
    ;;
  runtime)
    runtime_check
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
