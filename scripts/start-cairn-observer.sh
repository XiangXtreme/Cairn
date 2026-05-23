#!/usr/bin/env bash
set -euo pipefail

host="127.0.0.1"
port="8081"
runtime_dir=""
no_build="0"
no_browser="0"

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
    -h|--help)
      cat <<'EOF'
Usage: scripts/start-cairn-observer.sh [options]

Options:
  --host HOST             Bind host, default 127.0.0.1
  --port PORT             Bind port, default 8081
  --runtime-dir DIR       Cairn runtime directory, default auto-detect
  --no-build              Do not auto-prepare the local observer bundle
  --no-browser            Do not open browser on startup
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
elif [[ -d "$repo_root/.cairn-runtime/observer/runs" ]]; then
  runtime_dir="$repo_root/.cairn-runtime"
else
  runtime_dir="$repo_root/cairn/.cairn-runtime"
fi

if [[ "$no_build" != "1" ]]; then
  "$prepare_observer_script"
fi

mkdir -p "$runtime_dir"

export CAIRN_RUNS_DIR="$runtime_dir/observer/runs"
export AGENTSVIEW_DATA_DIR="$runtime_dir/agentsview-data"
export CAIRN_ONLY=1

echo "Starting Cairn Observer"
echo "  source: $observer_dir"
echo "  runs:   $CAIRN_RUNS_DIR"
echo "  data:   $AGENTSVIEW_DATA_DIR"
echo "  url:    http://$host:$port/"

args=(run -tags fts5 ./cmd/agentsview serve --host "$host" --port "$port")
if [[ "$no_browser" == "1" ]]; then
  args+=(--no-browser)
fi

cd "$observer_dir"
exec go "${args[@]}"
