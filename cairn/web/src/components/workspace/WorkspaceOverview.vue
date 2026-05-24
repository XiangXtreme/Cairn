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
      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">概览</div>
      <div class="mt-2 text-lg font-semibold">项目状态与工作台入口</div>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
        顶部区域汇总当前项目状态，下方项目区提供列表、图谱、时间线与操作入口。
      </p>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <article class="rounded-3xl border border-teal-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="teal">活跃</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ activeCount }}</div>
        <div class="mt-1 text-xs text-slate-500">当前正在推进的项目</div>
      </article>
      <article class="rounded-3xl border border-amber-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="amber">暂停</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ stoppedCount }}</div>
        <div class="mt-1 text-xs text-slate-500">等待进一步操作</div>
      </article>
      <article class="rounded-3xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="slate">完成</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ completedCount }}</div>
        <div class="mt-1 text-xs text-slate-500">
          {{ selectedProjectId ? `正在查看 ${selectedProjectId}` : '打开项目查看详情' }}
        </div>
      </article>
    </div>
  </section>
</template>
