#!/usr/bin/env bash
set -euo pipefail

force="0"

usage() {
  cat <<'EOF'
Usage: scripts/prepare-cairn-observer.sh [options]

Ensure the local Cairn observer bundle is ready for Docker/runtime use.

Options:
  --force     Rebuild frontend assets and the local agentsview binary
  -h, --help  Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      force="1"
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
observer_dir="$repo_root/observer/agentsview"
frontend_dir="$observer_dir/frontend"
embedded_dist="$observer_dir/internal/web/dist"
asset_dir="$embedded_dist/assets"
binary_path="$observer_dir/agentsview"

if [[ ! -d "$observer_dir" ]]; then
  echo "Cairn observer source not found: $observer_dir" >&2
  exit 1
fi

have_assets="0"
if [[ -d "$asset_dir" ]] && find "$asset_dir" -maxdepth 1 -type f -print -quit 2>/dev/null | grep -q .; then
  have_assets="1"
fi

assets_built="0"
if [[ "$force" == "1" || "$have_assets" != "1" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required to build Cairn observer frontend assets." >&2
    exit 1
  fi

  echo "Preparing Cairn observer frontend bundle"
  (
    cd "$frontend_dir"
    if [[ ! -d node_modules ]]; then
      npm install
    fi
    npm run build
  )

  rm -rf "$embedded_dist"
  mkdir -p "$(dirname "$embedded_dist")"
  cp -R "$frontend_dir/dist" "$embedded_dist"
  printf '%s\n' 'keep embed dir for generated frontend assets' > "$embedded_dist/.keep"
  assets_built="1"
fi

if [[ "$force" == "1" || "$assets_built" == "1" || ! -x "$binary_path" ]]; then
  if ! command -v go >/dev/null 2>&1; then
    echo "go is required to build the local agentsview binary." >&2
    exit 1
  fi

  echo "Preparing local Cairn observer binary"
  (
    cd "$observer_dir"
    CGO_ENABLED=1 go build -tags fts5 -o agentsview ./cmd/agentsview
  )
fi

echo "Cairn observer artifacts are ready."
