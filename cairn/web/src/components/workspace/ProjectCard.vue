<script setup lang="ts">
import { Activity, CheckCircle2, Clock3, Copy, Eye, Pause, Play, Trash2 } from 'lucide-vue-next';
import { computed } from 'vue';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import type { ProjectSummary } from '@/types/workspace';
import { projectStatusLabel, projectStatusTone } from '@/utils/workspace';

const props = defineProps<{
  project: ProjectSummary;
  selected?: boolean;
}>();

const emit = defineEmits<{
  open: [projectId: string];
  preview: [projectId: string];
  toggle: [projectId: string, nextStatus: 'active' | 'stopped'];
  clone: [projectId: string];
  delete: [projectId: string];
}>();

function nextStatus() {
  return props.project.status === 'active' ? 'stopped' : 'active';
}

const isRunning = computed(() => props.project.reason || props.project.working_intent_count > 0);
</script>

<template>
  <article
    class="rounded-3xl border bg-white p-4 shadow-sm transition"
    :class="selected ? 'border-brand-300 ring-2 ring-brand-100' : 'border-slate-200 hover:border-slate-300'"
  >
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,0.9fr)_minmax(0,1.2fr)_minmax(0,0.8fr)] xl:items-start">
      <div class="min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <h3 class="truncate text-base font-semibold text-slate-900">{{ project.title }}</h3>
              <BadgePill :tone="isRunning ? 'sky' : projectStatusTone(project.status)" :class="isRunning ? 'reason-chip-running' : ''">
                {{ isRunning ? '运行中' : projectStatusLabel(project.status) }}
              </BadgePill>
            </div>
            <div class="mt-1 text-xs font-mono text-slate-400">{{ project.id }}</div>
          </div>
          <button
            type="button"
            class="rounded-2xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            @click="emit('delete', project.id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>

        <div class="mt-4 flex items-center gap-2 text-xs text-slate-500">
          <Activity class="h-3.5 w-3.5" :class="isRunning ? 'text-sky-500' : ''" />
          <span v-if="project.reason">推理中：{{ project.reason.worker }} / {{ project.reason.trigger }}</span>
          <span v-else-if="project.working_intent_count > 0">执行中：{{ project.working_intent_count }} 个 intent 正在推进</span>
          <span v-else-if="project.status === 'completed'">已收敛完成</span>
          <span v-else-if="project.status === 'stopped'">已暂停，等待恢复</span>
          <span v-else>暂无推理租约</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4 xl:col-span-2">
        <div class="rounded-2xl bg-slate-50 px-2 py-3">
          <div class="font-semibold text-slate-900">{{ project.fact_count }}</div>
          <div class="mt-1 text-slate-400">事实</div>
        </div>
        <div class="rounded-2xl bg-slate-50 px-2 py-3">
          <div class="font-semibold text-slate-900">{{ project.intent_count }}</div>
          <div class="mt-1 text-slate-400">意图</div>
        </div>
        <div class="rounded-2xl bg-slate-50 px-2 py-3">
          <div class="font-semibold text-slate-900">{{ project.working_intent_count }}</div>
          <div class="mt-1 text-slate-400">运行中</div>
        </div>
        <div class="rounded-2xl bg-slate-50 px-2 py-3">
          <div class="font-semibold text-slate-900">{{ project.hint_count }}</div>
          <div class="mt-1 text-slate-400">提示</div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 xl:justify-end">
        <AppButton :icon="Eye" size="sm" variant="brand" @click="emit('open', project.id)">进入详情</AppButton>
        <AppButton :icon="project.status === 'active' ? Pause : Play" size="sm" @click="emit('toggle', project.id, nextStatus())">
          {{ project.status === 'active' ? '暂停' : '恢复' }}
        </AppButton>
        <AppButton :icon="Copy" size="sm" @click="emit('clone', project.id)">克隆</AppButton>
        <AppButton :icon="Clock3" size="sm" @click="emit('preview', project.id)">导出 / 时间线</AppButton>
        <CheckCircle2 v-if="project.status === 'completed'" class="h-4 w-4 text-slate-400" />
      </div>
    </div>
  </article>
</template>

<style scoped>
.reason-chip-running {
  animation: reasonChipGlow 1.8s ease-in-out infinite;
}

@keyframes reasonChipGlow {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(14, 165, 233, 0.14);
    transform: translateY(0);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(14, 165, 233, 0.08);
    transform: translateY(-1px);
  }
}
</style>
