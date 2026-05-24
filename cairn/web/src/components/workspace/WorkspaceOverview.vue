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
      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">全局概览</div>
      <div class="mt-2 text-lg font-semibold">运行中的探索与设置，终于分家了。</div>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
        上方是工作台层的全局状态，这里只关心项目节奏；下面的项目区负责具体图谱、时间线和操作，不再混成一片卡片海。
      </p>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <article class="rounded-3xl border border-teal-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="teal">活跃</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ activeCount }}</div>
        <div class="mt-1 text-xs text-slate-500">调度继续推进</div>
      </article>
      <article class="rounded-3xl border border-amber-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="amber">暂停</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ stoppedCount }}</div>
        <div class="mt-1 text-xs text-slate-500">等待人工恢复</div>
      </article>
      <article class="rounded-3xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
        <BadgePill tone="slate">完成</BadgePill>
        <div class="mt-3 text-2xl font-semibold text-slate-900">{{ completedCount }}</div>
        <div class="mt-1 text-xs text-slate-500">
          {{ selectedProjectId ? `当前聚焦 ${selectedProjectId}` : '可进入详情复盘' }}
        </div>
      </article>
    </div>
  </section>
</template>
