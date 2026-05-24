#!/usr/bin/env bash
set -euo pipefail

mode="${CAIRN_DISPATCH_SETTINGS_MODE:-ui}"
profile="all"
build="1"
logs="0"

usage() {
  cat <<'EOF'
Usage: scripts/start-cairn-docker.sh [options]

Start the primary Cairn runtime for the current checkout.

Options:
  --mode file|ui      Dispatcher config source, default ui
                     ui  -> datas/cairn/dispatch_ui.yaml, hot reloaded
                     file -> dispatch_docker.yaml, hot reloaded
  --server-only       Start only cairn-server
  --core-only         Start cairn-server and cairn-dispatcher
  --no-build          Do not rebuild the cairn image
  --logs              Follow logs after startup
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --server-only)
      profile="server"
      shift
      ;;
    --core-only)
      profile="core"
      shift
      ;;
    --no-build)
      build="0"
      shift
      ;;
    --logs)
      logs="1"
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

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
prepare_observer_script="$repo_root/scripts/prepare-cairn-observer.sh"

cd "$repo_root"

mkdir -p datas/cairn datas/cairn-runtime

if ! docker volume inspect cairn-worker-sessions >/dev/null 2>&1; then
  docker volume create cairn-worker-sessions >/dev/null
fi

services=(cairn-server)
if [[ "$profile" == "core" || "$profile" == "all" ]]; then
  services+=(cairn-dispatcher)
fi
if [[ "$profile" == "all" ]]; then
  services+=(cairn-observer)
fi

if [[ "$profile" == "all" ]]; then
  "$prepare_observer_script"
fi

compose=(docker compose up -d)
if [[ "$build" == "1" ]]; then
  compose+=(--build)
fi
compose+=("${services[@]}")

echo "Starting Cairn Docker runtime"
echo "  mode:     $mode"
echo "  services: ${services[*]}"
echo "  data:     $repo_root/datas"

CAIRN_DISPATCH_SETTINGS_MODE="$mode" "${compose[@]}"

cat <<EOF

Cairn is starting:
  Main UI:   http://127.0.0.1:8000
  Observer:  http://127.0.0.1:8081

Config mode:
  $mode

Useful commands:
  docker compose ps
  docker compose logs -f cairn-dispatcher
  ./scripts/dev-rebuild.sh check
EOF

if [[ "$profile" == "all" ]]; then
  cat <<'EOF'
  docker compose logs cairn-observer | rg 'Auth enabled\. Token:'
EOF
fi

if [[ "$logs" == "1" ]]; then
  docker compose logs -f "${services[@]}"
fi
