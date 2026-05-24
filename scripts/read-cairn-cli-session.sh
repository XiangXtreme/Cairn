#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/read-cairn-cli-session.sh [options]

Read a Cairn CLI session from AgentView's SQLite store, with Cairn run metadata.

Selectors:
  --session ID        Session id, with or without agent prefix (for example codex:... or 019e...)
  --project ID        Project id/name (for example proj_014, proj14, cairn_dispatch_proj_014)
  --run RUN_ID        Cairn worker run id from observer/runs
  --latest            Pick the latest matching session when multiple match (default)
  --list              List matching sessions only

Paths:
  --runtime-dir DIR   Runtime root, default datas/cairn-runtime
  --db PATH           AgentView sessions.db path

Output:
  --no-tools          Hide tool call detail
  --full              Print full message/tool content instead of previews
  --limit N           Max sessions to list, default 20

Examples:
  scripts/read-cairn-cli-session.sh --project proj14
  scripts/read-cairn-cli-session.sh --session 019e59ea-8e1f-7a23-a0a3-4e874c4dcc35
  scripts/read-cairn-cli-session.sh --run 2f9a2f8f6a9145eaa0c0781fb4458166
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"

runtime_dir="$repo_root/datas/cairn-runtime"
db_path=""
selector_session=""
selector_project=""
selector_run=""
list_only="0"
show_tools="1"
full_output="0"
limit="20"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)
      selector_session="${2:-}"
      shift 2
      ;;
    --project)
      selector_project="${2:-}"
      shift 2
      ;;
    --run)
      selector_run="${2:-}"
      shift 2
      ;;
    --runtime-dir)
      runtime_dir="${2:-}"
      shift 2
      ;;
    --db)
      db_path="${2:-}"
      shift 2
      ;;
    --latest)
      shift
      ;;
    --list)
      list_only="1"
      shift
      ;;
    --no-tools)
      show_tools="0"
      shift
      ;;
    --full)
      full_output="1"
      shift
      ;;
    --limit)
      limit="${2:-20}"
      shift 2
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

if [[ "$runtime_dir" != /* ]]; then
  runtime_dir="$repo_root/$runtime_dir"
fi

if [[ -z "$db_path" ]]; then
  for candidate in \
    "$runtime_dir/agentsview-data/sessions.db" \
    "$repo_root/.cairn-runtime/agentsview-data/sessions.db"
  do
    if [[ -s "$candidate" ]]; then
      db_path="$candidate"
      break
    fi
  done
fi

if [[ -z "$db_path" || ! -s "$db_path" ]]; then
  echo "AgentView sessions.db not found. Pass --db PATH or start/sync AgentView first." >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 is required" >&2
  exit 1
fi

sql_escape() {
  printf "%s" "$1" | sed "s/'/''/g"
}

pop_field() {
  local value="$1"
  printf "%s" "${value%%$'\x1f'*}"
}

shift_field() {
  local value="$1"
  if [[ "$value" == *$'\x1f'* ]]; then
    printf "%s" "${value#*$'\x1f'}"
  else
    printf ""
  fi
}

normalize_project() {
  local value="$1"
  if [[ "$value" =~ ^proj([0-9]+)$ ]]; then
    printf "proj_%03d" "${BASH_REMATCH[1]}"
    return
  fi
  if [[ "$value" =~ ^proj_([0-9]+)$ ]]; then
    printf "proj_%03d" "${BASH_REMATCH[1]}"
    return
  fi
  if [[ "$value" =~ ^cairn_dispatch_proj_([0-9]+)$ ]]; then
    printf "proj_%03d" "${BASH_REMATCH[1]}"
    return
  fi
  printf "%s" "$value"
}

run_record_paths=()
if [[ -n "$selector_run" ]]; then
  while IFS= read -r path; do
    [[ -n "$path" ]] && run_record_paths+=("$path")
  done < <(find "$runtime_dir/observer/runs" -type f -name "${selector_run}.json" 2>/dev/null | sort)
  if [[ "${#run_record_paths[@]}" -eq 0 ]]; then
    echo "No Cairn run record found for run id: $selector_run" >&2
    exit 1
  fi
  if [[ -z "$selector_session" ]]; then
    selector_session="$(sed -n 's/^[[:space:]]*"session_id":[[:space:]]*"\([^"]*\)".*/\1/p' "${run_record_paths[0]}" | head -1)"
  fi
  if [[ -z "$selector_project" ]]; then
    selector_project="$(sed -n 's/^[[:space:]]*"project_id":[[:space:]]*"\([^"]*\)".*/\1/p' "${run_record_paths[0]}" | head -1)"
  fi
fi

if [[ -z "$selector_session" && -z "$selector_project" ]]; then
  echo "Provide one selector: --session, --project, or --run." >&2
  usage >&2
  exit 2
fi

where_clause="1=1"
if [[ -n "$selector_session" ]]; then
  sid="$(sql_escape "$selector_session")"
  bare_sid="$sid"
  if [[ "$bare_sid" == *:* ]]; then
    bare_sid="${bare_sid#*:}"
  fi
  where_clause="(id = '$sid' OR id = 'codex:$bare_sid' OR id = 'claude:$bare_sid' OR id = 'pi:$bare_sid' OR source_session_id = '$sid' OR source_session_id = '$bare_sid')"
elif [[ -n "$selector_project" ]]; then
  project="$(normalize_project "$selector_project")"
  project_sql="$(sql_escape "$project")"
  project_display_sql="$(sql_escape "cairn_dispatch_${project}")"
  where_clause="(project = '$project_sql' OR project = '$project_display_sql' OR file_path LIKE '%$project_sql%' OR cwd LIKE '%$project_sql%')"
fi

session_rows="$(
  sqlite3 -separator $'\t' "$db_path" \
    "SELECT id, project, agent, COALESCE(started_at,''), message_count, COALESCE(file_path,''), COALESCE(cwd,'')
     FROM sessions
     WHERE $where_clause
     ORDER BY COALESCE(started_at, created_at) DESC, id DESC
     LIMIT $(printf '%d' "$limit");"
)"

if [[ -z "$session_rows" ]]; then
  echo "No AgentView session matched." >&2
  echo "db: $db_path" >&2
  echo "where: $where_clause" >&2
  exit 1
fi

echo "AgentView DB: $db_path"
echo
echo "Matching Sessions"
echo "$session_rows" | awk -F '\t' '{printf "- %s | project=%s | agent=%s | started=%s | messages=%s | file=%s\n", $1, $2, $3, $4, $5, $6}'

if [[ "$list_only" == "1" ]]; then
  exit 0
fi

session_id="$(printf "%s\n" "$session_rows" | head -1 | cut -f1)"
project_id="$(printf "%s\n" "$session_rows" | head -1 | cut -f2)"
agent_type="$(printf "%s\n" "$session_rows" | head -1 | cut -f3)"
session_file="$(printf "%s\n" "$session_rows" | head -1 | cut -f6)"

echo
echo "Selected Session"
echo "- id: $session_id"
echo "- project: $project_id"
echo "- agent: $agent_type"
echo "- file: ${session_file:-unknown}"

bare_session_id="${session_id#*:}"
echo
echo "Cairn Run Records"
run_match_count=0
while IFS= read -r run_path; do
  [[ -n "$run_path" ]] || continue
  run_match_count=$((run_match_count + 1))
  echo "- $run_path"
  sed -n \
    -e 's/^[[:space:]]*"run_id":[[:space:]]*"\([^"]*\)".*/  run_id: \1/p' \
    -e 's/^[[:space:]]*"project_id":[[:space:]]*"\([^"]*\)".*/  project_id: \1/p' \
    -e 's/^[[:space:]]*"intent_id":[[:space:]]*"\([^"]*\)".*/  intent_id: \1/p' \
    -e 's/^[[:space:]]*"phase":[[:space:]]*"\([^"]*\)".*/  phase: \1/p' \
    -e 's/^[[:space:]]*"worker_name":[[:space:]]*"\([^"]*\)".*/  worker: \1/p' \
    -e 's/^[[:space:]]*"status":[[:space:]]*"\([^"]*\)".*/  status: \1/p' \
    -e 's/^[[:space:]]*"duration_ms":[[:space:]]*\([^,]*\).*/  duration_ms: \1/p' \
    "$run_path"
  if command -v jq >/dev/null 2>&1; then
    jq -r 'if (.skill_ids // []) | length > 0 then "  skills: " + ((.skill_ids // []) | join(", ")) else empty end' "$run_path"
    jq -r 'if (.skill_names // []) | length > 0 then "  skill_names: " + ((.skill_names // []) | join(", ")) else empty end' "$run_path"
  else
    sed -n '/"skill_ids": \[/,/\]/p; /"skill_names": \[/,/\]/p' "$run_path" | sed 's/^/  /'
  fi
done < <(find "$runtime_dir/observer/runs" -type f -name '*.json' -print0 2>/dev/null \
  | xargs -0 grep -l "\"session_id\": \"${session_id}\"\\|\"session_id\": \"${bare_session_id}\"" 2>/dev/null \
  | sort)
if [[ "$run_match_count" -eq 0 ]]; then
  echo "- none found for $session_id"
fi

content_expr="content"
tool_input_expr="input_json"
tool_result_expr="result_content"
if [[ "$full_output" != "1" ]]; then
  content_expr="CASE WHEN length(content) > 1800 THEN substr(content, 1, 1800) || char(10) || '[... truncated; pass --full for full content]' ELSE content END"
  tool_input_expr="CASE WHEN length(input_json) > 1200 THEN substr(input_json, 1, 1200) || char(10) || '[... truncated; pass --full]' ELSE input_json END"
  tool_result_expr="CASE WHEN length(result_content) > 1600 THEN substr(result_content, 1, 1600) || char(10) || '[... truncated; pass --full]' ELSE result_content END"
fi

echo
echo "Messages"
sqlite3 -separator $'\x1f' -newline $'\x1e' "$db_path" \
  "SELECT ordinal, role, is_system, $content_expr
   FROM messages
   WHERE session_id = '$(sql_escape "$session_id")'
   ORDER BY ordinal;" |
while IFS= read -r -d $'\x1e' row; do
  ordinal="$(pop_field "$row")"
  row="$(shift_field "$row")"
  role="$(pop_field "$row")"
  row="$(shift_field "$row")"
  is_system="$(pop_field "$row")"
  content="$(shift_field "$row")"
  echo
  echo "[$ordinal] role=$role system=$is_system"
  printf "%s\n" "$content"
done

if [[ "$show_tools" == "1" ]]; then
  echo
  echo "Tool Calls"
  sqlite3 -separator $'\x1f' -newline $'\x1e' "$db_path" \
    "SELECT m.ordinal, t.tool_name, t.category, COALESCE(t.skill_name,''), COALESCE($tool_input_expr,''), COALESCE($tool_result_expr,'')
     FROM tool_calls t
     JOIN messages m ON m.id = t.message_id
     WHERE t.session_id = '$(sql_escape "$session_id")'
     ORDER BY m.ordinal, t.id;" |
  while IFS= read -r -d $'\x1e' row; do
    ordinal="$(pop_field "$row")"
    row="$(shift_field "$row")"
    tool_name="$(pop_field "$row")"
    row="$(shift_field "$row")"
    category="$(pop_field "$row")"
    row="$(shift_field "$row")"
    skill_name="$(pop_field "$row")"
    row="$(shift_field "$row")"
    input_json="$(pop_field "$row")"
    result_content="$(shift_field "$row")"
    echo
    echo "[$ordinal] tool=$tool_name category=$category skill=${skill_name:-none}"
    if [[ -n "$input_json" ]]; then
      echo "input:"
      printf "%s\n" "$input_json"
    fi
    if [[ -n "$result_content" ]]; then
      echo "result:"
      printf "%s\n" "$result_content"
    fi
  done
fi
