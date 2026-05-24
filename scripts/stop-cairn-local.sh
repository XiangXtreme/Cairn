#!/usr/bin/env bash
set -euo pipefail

stop_server="1"
stop_dispatcher="1"
stop_observer="1"

usage() {
  cat <<'EOF'
Usage: scripts/stop-cairn-local.sh [options]

Stop local Cairn background processes started from this repository.

Options:
  --server-only         Stop only cairn serve
  --dispatcher-only     Stop only cairn dispatch
  --observer-only       Stop only cairn observer
  -h, --help            Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-only)
      stop_dispatcher="0"
      stop_observer="0"
      shift
      ;;
    --dispatcher-only)
      stop_server="0"
      stop_observer="0"
      shift
      ;;
    --observer-only)
      stop_server="0"
      stop_dispatcher="0"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

server_pidfile="$repo_root/datas/cairn/server.pid"
dispatcher_pidfile="$repo_root/datas/cairn/dispatcher.pid"
observer_pidfile="$repo_root/datas/cairn/observer.pid"
observer_sync_pidfile="$repo_root/datas/cairn/observer-codex-sync.pid"
observer_sync_script="$repo_root/scripts/sync-cairn-codex-sessions.sh"

stop_pid_if_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi
  if ! ps -p "$pid" >/dev/null 2>&1; then
    return 1
  fi

  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if ps -p "$pid" >/dev/null 2>&1; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  return 0
}

find_repo_process_pids() {
  local pattern="$1"
  pgrep -af "$pattern" | awk -v repo="$repo_root" 'index($0, repo) { print $1 }'
}

stop_repo_processes() {
  local label="$1"
  local pattern="$2"
  local pids
  pids="$(find_repo_process_pids "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    return
  fi

  while read -r pid; do
    [[ -n "$pid" ]] || continue
    if stop_pid_if_running "$pid"; then
      echo "$label: stopped stale pid=$pid"
    fi
  done <<<"$pids"
}

clear_listener_port() {
  local clear_port="$1"
  local pids
  pids="$(lsof -tiTCP:"$clear_port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return
  fi
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    if stop_pid_if_running "$pid"; then
      echo "listener:$clear_port stopped pid=$pid"
    fi
  done <<<"$pids"
}

stop_from_pidfile() {
  local label="$1"
  local pidfile="$2"
  if [[ ! -f "$pidfile" ]]; then
    echo "$label: no pid file"
    return
  fi

  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    rm -f "$pidfile"
    echo "$label: empty pid file removed"
    return
  fi

  if stop_pid_if_running "$pid"; then
    echo "$label: stopped pid=$pid"
  else
    echo "$label: pid $pid already exited"
  fi

  rm -f "$pidfile"
}

echo "Stopping local Cairn processes"

if [[ "$stop_server" == "1" ]]; then
  stop_from_pidfile "server" "$server_pidfile"
  stop_repo_processes "server" "$repo_root/cairn/.venv/bin/cairn serve --host 0.0.0.0 --port 8000"
fi

if [[ "$stop_dispatcher" == "1" ]]; then
  stop_from_pidfile "dispatcher" "$dispatcher_pidfile"
  stop_repo_processes "dispatcher" "$repo_root/cairn/.venv/bin/cairn dispatch"
fi

if [[ "$stop_observer" == "1" ]]; then
  stop_from_pidfile "observer" "$observer_pidfile"
  stop_from_pidfile "observer-sync" "$observer_sync_pidfile"
  stop_repo_processes "observer" "$repo_root/observer/agentsview/agentsview serve --host 0.0.0.0 --port 8081"
  stop_repo_processes "observer-sync" "$observer_sync_script"
  stop_repo_processes "observer" "go run -tags fts5 ./cmd/agentsview serve --host 0.0.0.0 --port 8081"
  clear_listener_port "8081"
fi
