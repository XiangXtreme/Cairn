#!/usr/bin/env bash
set -euo pipefail

host="0.0.0.0"
port="8081"
runtime_dir=""
no_build="0"
no_browser="0"
observer_logs="0"

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
      cat <<'EOF'
Usage: scripts/start-cairn-observer.sh [options]

Options:
  --host HOST             Bind host, default 0.0.0.0
  --port PORT             Bind port, default 8081
  --runtime-dir DIR       Cairn runtime directory, default auto-detect
  --no-build              Do not auto-prepare the local observer bundle
  --no-browser            Do not open browser on startup
  --logs                  Follow observer log after startup
EOF
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
observer_dir="$repo_root/observer/agentsview"
prepare_observer_script="$repo_root/scripts/prepare-cairn-observer.sh"
observer_log="$repo_root/datas/cairn/observer.log"
observer_pidfile="$repo_root/datas/cairn/observer.pid"
observer_sync_pidfile="$repo_root/datas/cairn/observer-codex-sync.pid"
db_path="$repo_root/datas/cairn/cairn.db"
codex_sessions_root=""

if [[ ! -d "$observer_dir" ]]; then
  echo "Cairn observer source not found: $observer_dir" >&2
  exit 1
fi

if [[ -n "$runtime_dir" ]]; then
  if [[ "$runtime_dir" != /* ]]; then
    runtime_dir="$repo_root/$runtime_dir"
  fi
elif [[ -d "$repo_root/cairn/.cairn-runtime/observer/runs" ]]; then
  runtime_dir="$repo_root/cairn/.cairn-runtime"
elif [[ -d "$repo_root/datas/cairn-runtime/observer/runs" ]]; then
  runtime_dir="$repo_root/datas/cairn-runtime"
elif [[ -d "$repo_root/.cairn-runtime/observer/runs" ]]; then
  runtime_dir="$repo_root/.cairn-runtime"
else
  runtime_dir="$repo_root/datas/cairn-runtime"
fi

if [[ "$no_build" != "1" ]]; then
  "$prepare_observer_script"
fi

mkdir -p "$runtime_dir"
mkdir -p "$repo_root/datas/cairn"

codex_sessions_root="$runtime_dir/observer/codex-sessions"
rm -rf "$codex_sessions_root"
mkdir -p "$codex_sessions_root"

sync_codex_sessions() {
  mkdir -p "$codex_sessions_root"
  find "$codex_sessions_root" -xtype l -delete 2>/dev/null || true
  while IFS= read -r rollout_path; do
    [[ -n "$rollout_path" ]] || continue
    link_name="$(basename "$rollout_path")"
    target_path="$codex_sessions_root/$link_name"
    if [[ -e "$target_path" || -L "$target_path" ]]; then
      existing_target="$(readlink -f "$target_path" 2>/dev/null || true)"
      if [[ "$existing_target" == "$rollout_path" ]]; then
        continue
      fi
      stem="${link_name%.jsonl}"
      ext=".jsonl"
      suffix=1
      while [[ -e "$codex_sessions_root/${stem}-$suffix$ext" || -L "$codex_sessions_root/${stem}-$suffix$ext" ]]; do
        suffix=$((suffix + 1))
      done
      target_path="$codex_sessions_root/${stem}-$suffix$ext"
    fi
    ln -sfn "$rollout_path" "$target_path"
  done < <(find "$runtime_dir/projects" -type f -path '*/.cairn/codex-home/*/sessions/*/*/*/rollout-*.jsonl' | sort)
}

sync_codex_sessions

export CAIRN_RUNS_DIR="$runtime_dir/observer/runs"
export AGENTSVIEW_DATA_DIR="$runtime_dir/agentsview-data"
export CAIRN_ONLY=1
export CAIRN_DB_PATH="$db_path"
export CODEX_SESSIONS_DIR="$codex_sessions_root"

echo "Starting Cairn Observer"
echo "  source: $observer_dir"
echo "  runs:   $CAIRN_RUNS_DIR"
echo "  data:   $AGENTSVIEW_DATA_DIR"
echo "  db:     $CAIRN_DB_PATH"
echo "  codex:  $CODEX_SESSIONS_DIR"
echo "  url:    http://$host:$port/"

if [[ -f "$observer_pidfile" ]]; then
  old_pid="$(cat "$observer_pidfile" 2>/dev/null || true)"
  if [[ -n "${old_pid:-}" ]] && ps -p "$old_pid" >/dev/null 2>&1; then
    kill "$old_pid" >/dev/null 2>&1 || true
    sleep 1
  fi
fi

if [[ -f "$observer_sync_pidfile" ]]; then
  old_sync_pid="$(cat "$observer_sync_pidfile" 2>/dev/null || true)"
  if [[ -n "${old_sync_pid:-}" ]] && ps -p "$old_sync_pid" >/dev/null 2>&1; then
    kill "$old_sync_pid" >/dev/null 2>&1 || true
    sleep 1
  fi
fi

args=(go run -tags fts5 ./cmd/agentsview serve --host "$host" --port "$port")
if [[ "$no_browser" == "1" ]]; then
  args+=(--no-browser)
fi

(
  cd "$observer_dir"
  setsid env \
    CAIRN_RUNS_DIR="$CAIRN_RUNS_DIR" \
    AGENTSVIEW_DATA_DIR="$AGENTSVIEW_DATA_DIR" \
    CAIRN_ONLY="$CAIRN_ONLY" \
    CAIRN_DB_PATH="$CAIRN_DB_PATH" \
    CODEX_SESSIONS_DIR="$CODEX_SESSIONS_DIR" \
    "${args[@]}" >"$observer_log" 2>&1 < /dev/null &
  echo $! >"$observer_pidfile"
)

observer_pid="$(cat "$observer_pidfile")"
echo "  pid:    $observer_pid"
echo "  log:    $observer_log"

(
  while true; do
    sync_codex_sessions
    sleep 5
  done
) >/dev/null 2>&1 &
echo $! >"$observer_sync_pidfile"

if [[ "$observer_logs" == "1" ]]; then
  tail -f "$observer_log"
fi
