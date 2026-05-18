<script lang="ts">
  import { listCairnRuns } from "../../api/client.js";
  import type { CairnRun } from "../../api/types.js";
  import { formatDuration } from "../../utils/duration.js";

  interface Props {
    sessionId: string;
  }

  let { sessionId }: Props = $props();

  let runs = $state<CairnRun[]>([]);
  let configured = $state(false);
  let loading = $state(false);
  let error = $state<string | null>(null);

  $effect(() => {
    let cancelled = false;
    loading = true;
    error = null;
    void listCairnRuns({ session_id: sessionId, limit: 20 })
      .then((res) => {
        if (cancelled) return;
        configured = res.configured;
        runs = res.runs;
      })
      .catch((err) => {
        if (cancelled) return;
        error = err instanceof Error ? err.message : String(err);
        runs = [];
      })
      .finally(() => {
        if (!cancelled) loading = false;
      });

    return () => {
      cancelled = true;
    };
  });

  function statusClass(run: CairnRun): string {
    if (run.timed_out) return "timeout";
    if (run.cancelled) return "cancelled";
    return run.status.toLowerCase();
  }

  function statusLabel(run: CairnRun): string {
    if (run.timed_out) return "timeout";
    if (run.cancelled) return "cancelled";
    return run.status || "unknown";
  }

  function shortId(value?: string | null): string {
    if (!value) return "—";
    if (value.length <= 12) return value;
    return value.slice(0, 8);
  }

  function duration(run: CairnRun): string {
    return run.duration_ms == null ? "—" : formatDuration(run.duration_ms);
  }

  function previewLabel(text: string, stream: "stdout" | "stderr"): string {
    const lines = text.split(/\r?\n/).filter(Boolean).length;
    return `${stream} · ${lines || 1} line${lines === 1 ? "" : "s"}`;
  }

  function skillList(run: CairnRun): string[] {
    if (Array.isArray(run.skill_names) && run.skill_names.length > 0) {
      return run.skill_names;
    }
    if (Array.isArray(run.skill_ids) && run.skill_ids.length > 0) {
      return run.skill_ids;
    }
    return [];
  }
</script>

{#if configured && (runs.length > 0 || loading || error)}
  <section class="v-section cairn-section">
    <header class="v-h">
      <span>Cairn</span>
      <span class="v-meta">
        {#if loading}
          loading
        {:else if error}
          unavailable
        {:else}
          {runs.length} run{runs.length === 1 ? "" : "s"}
        {/if}
      </span>
    </header>

    {#if error}
      <p class="cairn-error">{error}</p>
    {:else}
      <div class="runs">
        {#each runs as run (run.run_id)}
          <article class="run">
            <div class="run-top">
              <span class="status" class:success={statusClass(run) === "success"} class:running={statusClass(run) === "running"} class:failed={statusClass(run) === "failed"} class:timeout={statusClass(run) === "timeout"} class:cancelled={statusClass(run) === "cancelled"}>
                {statusLabel(run)}
              </span>
              <span class="run-phase">{run.phase}</span>
              <span class="run-duration">{duration(run)}</span>
            </div>

            <div class="run-grid">
              <span>project</span>
              <strong>{run.project_id}</strong>
              <span>intent</span>
              <strong title={run.intent_id ?? ""}>{shortId(run.intent_id)}</strong>
              <span>worker</span>
              <strong>{run.worker_name}</strong>
              <span>agent</span>
              <strong>{run.agent_type}</strong>
              {#if skillList(run).length > 0}
                <span>skills</span>
                <strong title={skillList(run).join(", ")}>{skillList(run).join(", ")}</strong>
              {/if}
              {#if run.exit_code !== undefined && run.exit_code !== null}
                <span>exit</span>
                <strong>{run.exit_code}</strong>
              {/if}
            </div>

            {#if Array.isArray(run.skill_source_paths) && run.skill_source_paths.length > 0}
              <details>
                <summary>skill paths · {run.skill_source_paths.length}</summary>
                <pre>{run.skill_source_paths.join("\n")}</pre>
              </details>
            {/if}

            {#if run.cancel_reason}
              <div class="reason">{run.cancel_reason}</div>
            {/if}

            {#if run.stdout_preview}
              <details>
                <summary>{previewLabel(run.stdout_preview, "stdout")}</summary>
                <pre>{run.stdout_preview}</pre>
              </details>
            {/if}

            {#if run.stderr_preview}
              <details>
                <summary>{previewLabel(run.stderr_preview, "stderr")}</summary>
                <pre>{run.stderr_preview}</pre>
              </details>
            {/if}
          </article>
        {/each}
      </div>
    {/if}
  </section>
{/if}

<style>
  .cairn-section {
    border-bottom-color: color-mix(in srgb, var(--border-muted) 75%, #7dcfff);
  }

  .runs {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .run {
    border: 1px solid var(--border-muted);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--bg-elevated, #151515) 82%, #7dcfff 4%);
    padding: 8px;
  }

  .run-top {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 7px;
    margin-bottom: 8px;
    font-family: var(--font-mono);
    font-size: 10px;
  }

  .status {
    border: 1px solid var(--border-muted);
    border-radius: 2px;
    padding: 1px 5px;
    color: var(--text-muted);
    text-transform: lowercase;
  }

  .status.success {
    border-color: color-mix(in srgb, var(--running-fg, #6ad0a8) 50%, transparent);
    color: var(--running-fg, #6ad0a8);
  }

  .status.running {
    border-color: color-mix(in srgb, #7dcfff 55%, transparent);
    color: #7dcfff;
    animation: duration-pulse 1.6s ease-in-out infinite;
  }

  .status.failed,
  .status.timeout {
    border-color: color-mix(in srgb, var(--slow-fg, #ff806c) 55%, transparent);
    color: var(--slow-fg, #ff806c);
  }

  .status.cancelled {
    border-color: color-mix(in srgb, #d5a6ff 50%, transparent);
    color: #d5a6ff;
  }

  .run-phase {
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .run-duration {
    color: var(--text-muted);
  }

  .run-grid {
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr);
    gap: 4px 8px;
    font-family: var(--font-mono);
    font-size: 10px;
  }

  .run-grid span {
    color: var(--text-muted);
    text-transform: uppercase;
    font-size: 8px;
    letter-spacing: 0.4px;
  }

  .run-grid strong {
    color: var(--text-primary);
    font-weight: 500;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .reason {
    margin-top: 7px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 10px;
    line-height: 1.4;
  }

  details {
    margin-top: 7px;
    border-top: 1px solid var(--border-muted);
    padding-top: 6px;
  }

  summary {
    cursor: pointer;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 9px;
    outline: none;
  }

  summary:hover {
    color: var(--text-primary);
  }

  pre {
    margin: 6px 0 0;
    max-height: 140px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text-primary);
    background: var(--bg-inset, rgba(255, 255, 255, 0.04));
    border-radius: 2px;
    padding: 7px;
    font-family: var(--font-mono);
    font-size: 10px;
    line-height: 1.45;
  }

  .cairn-error {
    color: var(--slow-fg);
    font-family: var(--font-mono);
    font-size: 10px;
    margin: 0;
  }
</style>
