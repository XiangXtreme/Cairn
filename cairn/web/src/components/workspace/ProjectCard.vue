<script setup lang="ts">
import { Activity, CheckCircle2, ChevronDown, Clock3, Copy, Eye, Pause, Play, Trash2 } from 'lucide-vue-next';
import { computed, onBeforeUnmount, ref } from 'vue';

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
const menuOpen = ref(false);

const statusSummary = computed(() => {
  if (props.project.reason) return `推理中：${props.project.reason.worker}`;
  if (props.project.working_intent_count > 0) return `${props.project.working_intent_count} 个 intent 运行中`;
  if (props.project.status === 'completed') return '已完成收敛';
  if (props.project.status === 'stopped') return '已暂停';
  return '空闲';
});

const activitySummary = computed(() => {
  if (props.project.reason) return props.project.reason.trigger ? `触发 ${props.project.reason.trigger}` : '等待推理输出';
  if (props.project.working_intent_count > 0) return '正在推进图谱';
  if (props.project.status === 'completed') return '结果已固化到图谱';
  if (props.project.status === 'stopped') return '等待恢复后继续派发';
  return '暂无推理租约';
});

const metricItems = computed(() => [
  { label: '事实', value: props.project.fact_count, accent: false },
  { label: '意图', value: props.project.intent_count, accent: false },
  { label: '运行中', value: props.project.working_intent_count, accent: props.project.working_intent_count > 0 },
  { label: '提示', value: props.project.hint_count, accent: false },
]);

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
}

function closeMenu() {
  menuOpen.value = false;
}

function handleOpen() {
  closeMenu();
  emit('open', props.project.id);
}

function handleToggle() {
  closeMenu();
  emit('toggle', props.project.id, nextStatus());
}

function handleClone() {
  closeMenu();
  emit('clone', props.project.id);
}

function handlePreview() {
  closeMenu();
  emit('preview', props.project.id);
}

function handleDelete() {
  closeMenu();
  emit('delete', props.project.id);
}

onBeforeUnmount(() => {
  closeMenu();
});
</script>

<template>
  <article
    class="rounded-[24px] border bg-white px-4 py-4 shadow-sm transition"
    :class="selected ? 'border-brand-300 ring-2 ring-brand-100' : 'border-slate-200 hover:border-slate-300 hover:shadow-md'"
  >
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.95fr)_auto] xl:items-center">
      <button
        type="button"
        class="min-w-0 text-left"
        @click="handleOpen"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="truncate text-lg font-semibold text-slate-950">{{ project.title }}</h3>
              <BadgePill :tone="isRunning ? 'sky' : projectStatusTone(project.status)" :class="isRunning ? 'reason-chip-running' : ''">
                {{ isRunning ? '运行中' : projectStatusLabel(project.status) }}
              </BadgePill>
            </div>
            <div class="mt-1 text-xs font-mono text-slate-400">{{ project.id }}</div>
          </div>
          <CheckCircle2 v-if="project.status === 'completed'" class="mt-0.5 h-4 w-4 shrink-0 text-slate-300" />
        </div>

        <div class="mt-3 flex items-center gap-2 text-sm text-slate-600">
          <Activity class="h-3.5 w-3.5" :class="isRunning ? 'text-sky-500' : ''" />
          <span class="font-medium text-slate-700">{{ statusSummary }}</span>
        </div>
        <div class="mt-1.5 text-xs text-slate-500">{{ activitySummary }}</div>
      </button>

      <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div
          v-for="metric in metricItems"
          :key="metric.label"
          class="rounded-2xl border px-3 py-3 text-center transition"
          :class="metric.accent ? 'border-sky-200 bg-sky-50/70' : 'border-slate-200 bg-slate-50/80'"
        >
          <div class="text-lg font-semibold leading-none" :class="metric.accent ? 'text-sky-700' : 'text-slate-900'">
            {{ metric.value }}
          </div>
          <div class="mt-1 text-[11px] text-slate-500">{{ metric.label }}</div>
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-2">
        <AppButton :icon="Eye" size="sm" variant="brand" @click="handleOpen">进入详情</AppButton>
        <AppButton :icon="project.status === 'active' ? Pause : Play" size="sm" @click="handleToggle">
          {{ project.status === 'active' ? '暂停' : '恢复' }}
        </AppButton>
        <AppButton :icon="Copy" size="sm" @click="handleClone">克隆</AppButton>

        <div class="relative">
          <AppButton :icon="ChevronDown" size="sm" @click="toggleMenu">更多</AppButton>
          <div
            v-if="menuOpen"
            class="absolute right-0 top-[calc(100%+8px)] z-20 min-w-44 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-xl shadow-slate-200/70"
          >
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
              @click="handlePreview"
            >
              <Clock3 class="h-4 w-4" />
              <span>导出 / 时间线</span>
            </button>
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-rose-600 transition hover:bg-rose-50"
              @click="handleDelete"
            >
              <Trash2 class="h-4 w-4" />
              <span>删除项目</span>
            </button>
          </div>
        </div>
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
