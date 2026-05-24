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

  if ps -p "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if ps -p "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    echo "$label: stopped pid=$pid"
  else
    echo "$label: pid $pid already exited"
  fi

  rm -f "$pidfile"
}

echo "Stopping local Cairn processes"

if [[ "$stop_server" == "1" ]]; then
  stop_from_pidfile "server" "$server_pidfile"
fi

if [[ "$stop_dispatcher" == "1" ]]; then
  stop_from_pidfile "dispatcher" "$dispatcher_pidfile"
fi

if [[ "$stop_observer" == "1" ]]; then
  stop_from_pidfile "observer" "$observer_pidfile"
fi
