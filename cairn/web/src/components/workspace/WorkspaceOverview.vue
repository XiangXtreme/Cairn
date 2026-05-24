<script setup lang="ts">
import BadgePill from '@/components/ui/BadgePill.vue';

defineProps<{
  activeCount: number;
  stoppedCount: number;
  completedCount: number;
  selectedProjectId?: string;
}>();
</script>

<template>
  <section class="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
    <div class="rounded-3xl border border-slate-200 bg-slate-950 px-5 py-5 text-white shadow-sm">
      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Overview</div>
      <div class="mt-2 text-lg font-semibold">Project status and workspace entry points</div>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
        The top section summarizes current project status. The project area below provides list, graph, timeline, and action entry points.
      </p>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <article class="rounded-3xl border border-teal-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="teal">Active</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ activeCount }}</div>
        <div class="mt-1 text-xs text-slate-500">Projects currently in progress</div>
      </article>
      <article class="rounded-3xl border border-amber-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="amber">Paused</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ stoppedCount }}</div>
        <div class="mt-1 text-xs text-slate-500">Waiting for further action</div>
      </article>
      <article class="rounded-3xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="slate">Completed</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ completedCount }}</div>
        <div class="mt-1 text-xs text-slate-500">
          {{ selectedProjectId ? `Viewing ${selectedProjectId}` : 'Open a project to review details' }}
        </div>
      </article>
    </div>
  </section>
</template>
