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
  help      Show this help

Examples:
  ./scripts/dev-rebuild.sh cairn
  ./scripts/dev-rebuild.sh observer
  ./scripts/dev-rebuild.sh all
  ./scripts/dev-rebuild.sh check
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
observer_dir="$repo_root/observer/agentsview"

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

  log "Building agentsview frontend bundle"
  (
    cd "$observer_dir/frontend"
    npm run build
  )

  log "Syncing frontend bundle into embedded web assets"
  rm -rf "$observer_dir/internal/web/dist"
  cp -r "$observer_dir/frontend/dist" "$observer_dir/internal/web/dist"

  log "Building local agentsview binary with FTS5"
  (
    cd "$observer_dir"
    CGO_ENABLED=1 go build -tags fts5 -o agentsview ./cmd/agentsview
  )

  log "Starting/restarting cairn-observer"
  docker compose up -d cairn-observer
  docker compose restart cairn-observer
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
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
