#!/usr/bin/env bash
set -euo pipefail

host="0.0.0.0"
port="8081"
runtime_dir=""
no_build="0"
no_browser="0"
observer_logs="0"

usage() {
  cat <<'EOF'
Usage: scripts/start-cairn-observer.sh [options]

Dev-only fallback for starting the local Cairn AgentView observer.
The primary product path is Docker, where observer is managed by the main stack.

Options:
  --host HOST             Bind host, default 0.0.0.0
  --port PORT             Bind port, must be 8081
  --runtime-dir DIR       Runtime root, default datas/cairn-runtime
  --no-build              Do not auto-prepare the local observer bundle
  --no-browser            Do not open browser on startup
  --logs                  Follow observer log after startup
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      host="$2"
      shift 2
      ;;
    --port)
      port="$2"
      shift 2
      ;;
    --runtime-dir)
      runtime_dir="$2"
      shift 2
      ;;
    --no-build)
      no_build="1"
      shift
      ;;
    --no-browser)
      no_browser="1"
      shift
      ;;
    --logs)
      observer_logs="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$port" != "8081" ]]; then
  echo "Cairn observer is managed on a fixed port only: 8081" >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
observer_dir="$repo_root/observer/agentsview"
prepare_observer_script="$repo_root/scripts/prepare-cairn-observer.sh"
observer_binary="$observer_dir/agentsview"
sync_script="$repo_root/scripts/sync-cairn-agent-sessions.sh"
observer_log="$repo_root/datas/cairn/observer.log"
observer_pidfile="$repo_root/datas/cairn/observer.pid"
observer_sync_pidfile="$repo_root/datas/cairn/observer-codex-sync.pid"
db_path="$repo_root/datas/cairn/cairn.db"

if [[ ! -d "$observer_dir" ]]; then
  echo "Cairn observer source not found: $observer_dir" >&2
  exit 1
fi

if [[ -n "$runtime_dir" ]]; then
  if [[ "$runtime_dir" != /* ]]; then
    runtime_dir="$repo_root/$runtime_dir"
  fi
else
  runtime_dir="$repo_root/datas/cairn-runtime"
fi

if [[ "$no_build" != "1" ]]; then
  "$prepare_observer_script"
fi

if [[ ! -x "$observer_binary" ]]; then
  echo "Cairn observer binary not found or not executable: $observer_binary" >&2
  exit 1
fi

if [[ ! -x "$sync_script" ]]; then
  echo "Cairn observer sync helper not found or not executable: $sync_script" >&2
  exit 1
fi

mkdir -p "$runtime_dir/observer/runs"
mkdir -p "$runtime_dir/observer/codex-sessions"
mkdir -p "$runtime_dir/observer/claude-projects"
mkdir -p "$runtime_dir/observer/pi-sessions"
mkdir -p "$runtime_dir/agentsview-data"
mkdir -p "$repo_root/datas/cairn"

export CAIRN_RUNS_DIR="$runtime_dir/observer/runs"
export AGENTSVIEW_DATA_DIR="$runtime_dir/agentsview-data"
export CAIRN_ONLY=1
export CAIRN_DB_PATH="$db_path"
export CODEX_SESSIONS_DIR="$runtime_dir/observer/codex-sessions"
export CLAUDE_PROJECTS_DIR="$runtime_dir/observer/claude-projects"
export PI_DIR="$runtime_dir/observer/pi-sessions"
export CAIRN_SHARED_SESSIONS_ROOT="$repo_root/datas/cairn-observer-shared"

mkdir -p "$CAIRN_SHARED_SESSIONS_ROOT/.codex/sessions"
mkdir -p "$CAIRN_SHARED_SESSIONS_ROOT/.claude/projects"
mkdir -p "$CAIRN_SHARED_SESSIONS_ROOT/.pi/agent/sessions"

stop_pid_if_running() {
  local pid="$1"
  if [[ -z "$pid" ]] || ! ps -p "$pid" >/dev/null 2>&1; then
    return 1
  fi
  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if ps -p "$pid" >/dev/null 2>&1; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  return 0
}

stop_from_pidfile() {
  local pidfile="$1"
  if [[ ! -f "$pidfile" ]]; then
    return
  fi
  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  stop_pid_if_running "$pid" || true
  rm -f "$pidfile"
}

find_repo_process_pids() {
  local pattern="$1"
  pgrep -af "$pattern" | awk -v repo="$repo_root" 'index($0, repo) { print $1 }'
}

stop_repo_processes() {
  local pattern="$1"
  local pids
  pids="$(find_repo_process_pids "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    return
  fi
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    stop_pid_if_running "$pid" || true
  done <<<"$pids"
}

wait_for_port() {
  local wait_port="$1"
  local timeout_secs="${2:-15}"
  local start_ts
  start_ts="$(date +%s)"
  while true; do
    if ss -ltn "( sport = :$wait_port )" | tail -n +2 | grep -q .; then
      return 0
    fi
    if (( $(date +%s) - start_ts >= timeout_secs )); then
      return 1
    fi
    sleep 1
  done
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
    stop_pid_if_running "$pid" || true
    echo "observer: cleared listener pid=$pid on port $clear_port"
  done <<<"$pids"
}

find_managed_pid() {
  pgrep -af "$observer_binary serve --host $host --port $port" | awk -v repo="$repo_root" 'index($0, repo) { print $1; exit }'
}

echo "Starting Cairn Observer (fallback/dev-only)"
echo "  runtime_dir:         $runtime_dir"
echo "  CAIRN_RUNS_DIR:      $CAIRN_RUNS_DIR"
echo "  CODEX_SESSIONS_DIR:  $CODEX_SESSIONS_DIR"
echo "  CLAUDE_PROJECTS_DIR: $CLAUDE_PROJECTS_DIR"
echo "  PI_DIR:              $PI_DIR"
echo "  AGENTSVIEW_DATA_DIR: $AGENTSVIEW_DATA_DIR"
echo "  CAIRN_DB_PATH:       $CAIRN_DB_PATH"
echo "  listen:              http://$host:$port/"

stop_from_pidfile "$observer_pidfile"
stop_from_pidfile "$observer_sync_pidfile"
stop_repo_processes "$observer_binary serve --host $host --port $port"
stop_repo_processes "$sync_script"
stop_repo_processes "go run -tags fts5 ./cmd/agentsview serve --host $host --port $port"
clear_listener_port "$port"

if ss -ltn "( sport = :$port )" | tail -n +2 | grep -q .; then
  echo "Port $port is still occupied after cleanup; aborting." >&2
  exit 1
fi

: >"$observer_log"

main_cmd=(
  env
  CAIRN_RUNS_DIR="$CAIRN_RUNS_DIR"
  AGENTSVIEW_DATA_DIR="$AGENTSVIEW_DATA_DIR"
  CAIRN_ONLY="$CAIRN_ONLY"
  CAIRN_DB_PATH="$CAIRN_DB_PATH"
  CODEX_SESSIONS_DIR="$CODEX_SESSIONS_DIR"
  "$observer_binary"
  serve
  --host "$host"
  --port "$port"
)
if [[ "$no_browser" == "1" ]]; then
  main_cmd+=(--no-browser)
fi

setsid -f "${main_cmd[@]}" >>"$observer_log" 2>&1
sleep 1
observer_pid="$(find_managed_pid || true)"
if [[ -z "$observer_pid" ]] || ! ps -p "$observer_pid" >/dev/null 2>&1; then
  echo "Observer failed to stay running" >&2
  tail -n 60 "$observer_log" >&2 || true
  exit 1
fi
echo "$observer_pid" >"$observer_pidfile"

if ! wait_for_port "$port" 20; then
  echo "Observer failed to bind $host:$port" >&2
  tail -n 60 "$observer_log" >&2 || true
  exit 1
fi

setsid -f env \
  CAIRN_RUNTIME_DIR="$runtime_dir" \
  CODEX_SESSIONS_DIR="$CODEX_SESSIONS_DIR" \
  "$sync_script" >>"$observer_log" 2>&1
sleep 1
sync_pid="$(pgrep -af "$sync_script" | awk -v repo="$repo_root" 'index($0, repo) { print $1; exit }')"
if [[ -z "$sync_pid" ]] || ! ps -p "$sync_pid" >/dev/null 2>&1; then
  echo "Observer sync process failed to stay running" >&2
  tail -n 60 "$observer_log" >&2 || true
  exit 1
fi
echo "$sync_pid" >"$observer_sync_pidfile"

echo "  pid:                 $observer_pid"
echo "  sync pid:            $sync_pid"
echo "  log:                 $observer_log"

if [[ "$observer_logs" == "1" ]]; then
  tail -f "$observer_log"
fi
