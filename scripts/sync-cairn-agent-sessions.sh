#!/usr/bin/env bash
set -euo pipefail

runtime_dir="${CAIRN_RUNTIME_DIR:-}"
codex_sessions_dir="${CODEX_SESSIONS_DIR:-}"
claude_projects_dir="${CLAUDE_PROJECTS_DIR:-}"
pi_sessions_dir="${PI_DIR:-}"
shared_sessions_root="${CAIRN_SHARED_SESSIONS_ROOT:-}"
run_once="0"

if [[ "${1:-}" == "--once" ]]; then
  run_once="1"
fi

if [[ -z "$runtime_dir" ]]; then
  echo "sync-cairn-agent-sessions: CAIRN_RUNTIME_DIR is required" >&2
  exit 1
fi

mkdir -p "${codex_sessions_dir:-/tmp/unused-codex}"
mkdir -p "${claude_projects_dir:-/tmp/unused-claude}"
mkdir -p "${pi_sessions_dir:-/tmp/unused-pi}"

link_file() {
  local source_path="$1"
  local target_dir="$2"
  local prefix="$3"

  [[ -n "$source_path" && -n "$target_dir" ]] || return 0
  mkdir -p "$target_dir"

  local base_name
  base_name="$(basename "$source_path")"
  local target_path="$target_dir/${prefix}${base_name}"

  if [[ -e "$target_path" || -L "$target_path" ]]; then
    local existing_target
    existing_target="$(readlink -f "$target_path" 2>/dev/null || true)"
    if [[ "$existing_target" == "$source_path" ]]; then
      return 0
    fi
    local stem="${prefix}${base_name%.*}"
    local ext=""
    if [[ "$base_name" == *.* ]]; then
      ext=".${base_name##*.}"
    fi
    local suffix=1
    while [[ -e "$target_dir/${stem}-$suffix$ext" || -L "$target_dir/${stem}-$suffix$ext" ]]; do
      suffix=$((suffix + 1))
    done
    target_path="$target_dir/${stem}-$suffix$ext"
  fi

  ln -sfn "$source_path" "$target_path"
}

cleanup_broken_links() {
  local target_dir="$1"
  [[ -d "$target_dir" ]] || return 0
  find "$target_dir" -type l -delete 2>/dev/null || true
}

cleanup_prefixed_files() {
  local target_dir="$1"
  local prefix="$2"
  [[ -d "$target_dir" ]] || return 0
  find "$target_dir" -maxdepth 1 \( -type l -o -type f \) -name "${prefix}*" -delete 2>/dev/null || true
}

sync_codex() {
  [[ -n "$codex_sessions_dir" ]] || return 0
  cleanup_broken_links "$codex_sessions_dir"
  cleanup_prefixed_files "$codex_sessions_dir" "shared-"

  while IFS= read -r rollout_path; do
    [[ -n "$rollout_path" ]] || continue
    link_file "$rollout_path" "$codex_sessions_dir" ""
  done < <(find "$runtime_dir/projects" -type f -path '*/.cairn/codex-home/*/sessions/*/*/*/rollout-*.jsonl' 2>/dev/null | sort)

  if [[ -n "$shared_sessions_root" && -d "$shared_sessions_root/.codex/sessions" ]]; then
    while IFS= read -r rollout_path; do
      [[ -n "$rollout_path" ]] || continue
      link_file "$rollout_path" "$codex_sessions_dir" "shared-"
    done < <(find "$shared_sessions_root/.codex/sessions" -type f -name 'rollout-*.jsonl' 2>/dev/null | sort)
  fi
}

sync_claude() {
  [[ -n "$claude_projects_dir" ]] || return 0
  cleanup_broken_links "$claude_projects_dir"

  while IFS= read -r session_path; do
    [[ -n "$session_path" ]] || continue
    local project_name
    project_name="$(basename "$(dirname "$session_path")")"
    link_file "$session_path" "$claude_projects_dir/$project_name" ""
  done < <(find "$runtime_dir/projects" -type f -path '*/.cairn/claude-home/*/projects/*/*.jsonl' 2>/dev/null | sort)

  if [[ -n "$shared_sessions_root" && -d "$shared_sessions_root/.claude/projects" ]]; then
    while IFS= read -r session_path; do
      [[ -n "$session_path" ]] || continue
      local project_name
      project_name="$(basename "$(dirname "$session_path")")"
      cleanup_prefixed_files "$claude_projects_dir/$project_name" "shared-"
      link_file "$session_path" "$claude_projects_dir/$project_name" "shared-"
    done < <(find "$shared_sessions_root/.claude/projects" -type f -name '*.jsonl' 2>/dev/null | sort)
  fi
}

sync_pi() {
  [[ -n "$pi_sessions_dir" ]] || return 0
  cleanup_broken_links "$pi_sessions_dir"

  if [[ -n "$shared_sessions_root" && -d "$shared_sessions_root/.pi/agent/sessions" ]]; then
    while IFS= read -r session_path; do
      [[ -n "$session_path" ]] || continue
      local leaf_dir
      leaf_dir="$(basename "$(dirname "$session_path")")"
      cleanup_prefixed_files "$pi_sessions_dir/$leaf_dir" "shared-"
      link_file "$session_path" "$pi_sessions_dir/$leaf_dir" ""
    done < <(find "$shared_sessions_root/.pi/agent/sessions" -type f -name '*.jsonl' 2>/dev/null | sort)
  fi
}

sync_once() {
  sync_codex
  sync_claude
  sync_pi
}

echo "observer-sync: runtime_dir=$runtime_dir codex=$codex_sessions_dir claude=$claude_projects_dir pi=$pi_sessions_dir shared_root=$shared_sessions_root once=$run_once"

if [[ "$run_once" == "1" ]]; then
  sync_once
  exit 0
fi

while true; do
  sync_once
  sleep 5
done
