#!/usr/bin/env bash
set -euo pipefail

runtime_dir="${CAIRN_RUNTIME_DIR:-}"
codex_sessions_dir="${CODEX_SESSIONS_DIR:-}"

if [[ -z "$runtime_dir" || -z "$codex_sessions_dir" ]]; then
  echo "sync-cairn-codex-sessions: CAIRN_RUNTIME_DIR and CODEX_SESSIONS_DIR are required" >&2
  exit 1
fi

mkdir -p "$codex_sessions_dir"

sync_once() {
  find "$codex_sessions_dir" -xtype l -delete 2>/dev/null || true
  while IFS= read -r rollout_path; do
    [[ -n "$rollout_path" ]] || continue
    link_name="$(basename "$rollout_path")"
    target_path="$codex_sessions_dir/$link_name"
    if [[ -e "$target_path" || -L "$target_path" ]]; then
      existing_target="$(readlink -f "$target_path" 2>/dev/null || true)"
      if [[ "$existing_target" == "$rollout_path" ]]; then
        continue
      fi
      stem="${link_name%.jsonl}"
      ext=".jsonl"
      suffix=1
      while [[ -e "$codex_sessions_dir/${stem}-$suffix$ext" || -L "$codex_sessions_dir/${stem}-$suffix$ext" ]]; do
        suffix=$((suffix + 1))
      done
      target_path="$codex_sessions_dir/${stem}-$suffix$ext"
    fi
    ln -sfn "$rollout_path" "$target_path"
  done < <(find "$runtime_dir/projects" -type f -path '*/.cairn/codex-home/*/sessions/*/*/*/rollout-*.jsonl' 2>/dev/null | sort)
}

echo "observer-sync: runtime_dir=$runtime_dir codex_sessions_dir=$codex_sessions_dir"
while true; do
  sync_once
  sleep 5
done
