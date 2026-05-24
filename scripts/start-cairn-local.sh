#!/usr/bin/env bash
set -euo pipefail

mode="${CAIRN_DISPATCH_SETTINGS_MODE:-ui}"
start_server="1"
start_dispatcher="1"
server_logs="0"
dispatcher_logs="0"

usage() {
  cat <<'EOF'
Usage: scripts/start-cairn-local.sh [options]

Start the local Cairn server and/or dispatcher with repository-scoped data paths.

Options:
  --mode file|ui        Dispatcher config source, default ui
  --server-only         Start only cairn serve
  --dispatcher-only     Start only cairn dispatch
  --server-logs         Follow local server log after startup
  --dispatcher-logs     Follow local dispatcher log after startup
  -h, --help            Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --server-only)
      start_dispatcher="0"
      shift
      ;;
    --dispatcher-only)
      start_server="0"
      shift
      ;;
    --server-logs)
      server_logs="1"
      shift
      ;;
    --dispatcher-logs)
      dispatcher_logs="1"
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

if [[ "$mode" != "file" && "$mode" != "ui" ]]; then
  echo "--mode must be either file or ui" >&2
  exit 2
fi

if [[ "$start_server" != "1" && "$start_dispatcher" != "1" ]]; then
  echo "nothing to start" >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

cd "$repo_root"

mkdir -p datas/cairn datas/cairn-runtime

db_path="$repo_root/datas/cairn/cairn.db"
ui_dispatch_path="$repo_root/datas/cairn/dispatch_ui.yaml"
runtime_dir="$repo_root/datas/cairn-runtime"
server_log="$repo_root/datas/cairn/server.log"
dispatcher_log="$repo_root/datas/cairn/dispatcher.log"
server_pidfile="$repo_root/datas/cairn/server.pid"
dispatcher_pidfile="$repo_root/datas/cairn/dispatcher.pid"

common_env=(
  "CAIRN_UI_DISPATCH_CONFIG=$ui_dispatch_path"
  "CAIRN_DISPATCH_SETTINGS_MODE=$mode"
  "CAIRN_RUNTIME_DIR=$runtime_dir"
  "PYTHONPATH=$repo_root/cairn/src"
)

wait_for_port() {
  local port="$1"
  local timeout_secs="${2:-15}"
  local start_ts
  start_ts="$(date +%s)"
  while true; do
    if ss -ltn "( sport = :$port )" | tail -n +2 | grep -q .; then
      return 0
    fi
    if (( $(date +%s) - start_ts >= timeout_secs )); then
      return 1
    fi
    sleep 1
  done
}

stop_pid_if_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return
  fi
  if ps -p "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if ps -p "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
}

find_repo_process_pids() {
  local pattern="$1"
  pgrep -af "$pattern" | awk -v repo="$repo_root" 'index($0, repo) { print $1 }'
}

stop_repo_processes() {
  local pattern="$1"
  local label="$2"
  local pids
  pids="$(find_repo_process_pids "$pattern" || true)"
  if [[ -z "$pids" ]]; then
    return
  fi

  while read -r pid; do
    [[ -n "$pid" ]] || continue
    stop_pid_if_running "$pid"
    echo "$label: stopped stale pid=$pid"
  done <<<"$pids"
}

start_background_process() {
  local pidfile="$1"
  local logfile="$2"
  shift 2

  : >"$logfile"
  nohup env "${common_env[@]}" "$@" >>"$logfile" 2>&1 </dev/null &
  local pid=$!
  echo "$pid" >"$pidfile"
  echo "$pid"
}

start_server_cmd() {
  if [[ -f "$server_pidfile" ]]; then
    old_pid="$(cat "$server_pidfile" 2>/dev/null || true)"
    stop_pid_if_running "${old_pid:-}"
  fi
  stop_repo_processes "$repo_root/cairn/.venv/bin/cairn serve --host 0.0.0.0 --port 8000" "server"

  server_pid="$(
    cd "$repo_root" &&
      start_background_process \
        "$server_pidfile" \
        "$server_log" \
        "$repo_root/cairn/.venv/bin/cairn" \
        serve \
        --host 0.0.0.0 \
        --port 8000 \
        --db-path "$db_path"
  )"
  if ! wait_for_port 8000 15; then
    echo "Server failed to bind 0.0.0.0:8000" >&2
    tail -n 40 "$server_log" >&2 || true
    exit 1
  fi
  echo "Server started: pid=$server_pid"
  echo "  db:   $db_path"
  echo "  log:  $server_log"
}

start_dispatcher_cmd() {
  if [[ -f "$dispatcher_pidfile" ]]; then
    old_pid="$(cat "$dispatcher_pidfile" 2>/dev/null || true)"
    stop_pid_if_running "${old_pid:-}"
  fi
  stop_repo_processes "$repo_root/cairn/.venv/bin/cairn dispatch" "dispatcher"

  dispatcher_pid="$(
    cd "$repo_root" &&
      start_background_process \
        "$dispatcher_pidfile" \
        "$dispatcher_log" \
        "$repo_root/cairn/.venv/bin/cairn" \
        dispatch
  )"
  sleep 1
  if ! ps -p "$dispatcher_pid" >/dev/null 2>&1; then
    echo "Dispatcher failed to stay running" >&2
    tail -n 40 "$dispatcher_log" >&2 || true
    exit 1
  fi
  echo "Dispatcher started: pid=$dispatcher_pid"
  echo "  mode: $mode"
  echo "  log:  $dispatcher_log"
}

echo "Starting local Cairn"
echo "  repo:    $repo_root"
echo "  mode:    $mode"
echo "  runtime: $runtime_dir"

if [[ "$start_server" == "1" ]]; then
  start_server_cmd
fi

if [[ "$start_dispatcher" == "1" ]]; then
  start_dispatcher_cmd
fi

if [[ "$server_logs" == "1" && "$start_server" == "1" ]]; then
  tail -f "$server_log"
fi

if [[ "$dispatcher_logs" == "1" && "$start_dispatcher" == "1" ]]; then
  tail -f "$dispatcher_log"
fi
