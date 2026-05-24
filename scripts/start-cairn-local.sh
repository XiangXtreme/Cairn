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

start_server_cmd() {
  if [[ -f "$server_pidfile" ]]; then
    old_pid="$(cat "$server_pidfile" 2>/dev/null || true)"
    if [[ -n "${old_pid:-}" ]] && ps -p "$old_pid" >/dev/null 2>&1; then
      kill "$old_pid" >/dev/null 2>&1 || true
      sleep 1
    fi
  fi

  bash -lc "cd '$repo_root' && setsid env ${common_env[*]@Q} '$repo_root/cairn/.venv/bin/cairn' serve --host 0.0.0.0 --port 8000 --db-path '$db_path' >'$server_log' 2>&1 < /dev/null & echo \$!" >"$server_pidfile"
  server_pid="$(cat "$server_pidfile")"
  echo "$server_pid" >"$server_pidfile"
  echo "Server started: pid=$server_pid"
  echo "  db:   $db_path"
  echo "  log:  $server_log"
}

start_dispatcher_cmd() {
  if [[ -f "$dispatcher_pidfile" ]]; then
    old_pid="$(cat "$dispatcher_pidfile" 2>/dev/null || true)"
    if [[ -n "${old_pid:-}" ]] && ps -p "$old_pid" >/dev/null 2>&1; then
      kill "$old_pid" >/dev/null 2>&1 || true
      sleep 1
    fi
  fi

  bash -lc "cd '$repo_root' && setsid env ${common_env[*]@Q} '$repo_root/cairn/.venv/bin/cairn' dispatch >'$dispatcher_log' 2>&1 < /dev/null & echo \$!" >"$dispatcher_pidfile"
  dispatcher_pid="$(cat "$dispatcher_pidfile")"
  echo "$dispatcher_pid" >"$dispatcher_pidfile"
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
