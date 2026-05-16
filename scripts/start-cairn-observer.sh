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
  --no-build              Do not auto-build missing frontend assets
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
frontend_dir="$observer_dir/frontend"
embedded_dist="$observer_dir/internal/web/dist"
asset_dir="$embedded_dist/assets"

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

if [[ "$no_build" != "1" && ( ! -d "$asset_dir" || -z "$(find "$asset_dir" -maxdepth 1 -type f -print -quit 2>/dev/null)" ) ]]; then
  echo "Observer frontend assets are missing; building frontend..."
  (cd "$frontend_dir" && npm install && npm run build)
  rm -rf "$embedded_dist"
  mkdir -p "$(dirname "$embedded_dist")"
  cp -R "$frontend_dir/dist" "$embedded_dist"
  printf '%s\n' 'keep embed dir for generated frontend assets' > "$embedded_dist/.keep"
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
