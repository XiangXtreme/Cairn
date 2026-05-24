<script setup lang="ts">
import BadgePill from '@/components/ui/BadgePill.vue';
import type { TimelineEntry } from '@/types/workspace';

defineProps<{
  entries: TimelineEntry[];
  selectedEntryId?: string | null;
}>();

const emit = defineEmits<{
  open: [entry: TimelineEntry];
}>();

function toneFor(entry: TimelineEntry) {
  if (entry.type === 'project_completed') return 'rose';
  if (entry.type === 'intent_concluded') return 'teal';
  if (entry.type === 'intent_declared') return 'brand';
  if (entry.type === 'hint_added') return 'amber';
  return 'slate';
}

function labelFor(entry: TimelineEntry) {
  if (entry.type === 'project_created') return '项目创建';
  if (entry.type === 'hint_added') return '提示';
  if (entry.type === 'reason_started') return '推理';
  if (entry.type === 'intent_running') return '执行中';
  if (entry.type === 'intent_declared') return '意图';
  if (entry.type === 'intent_concluded') return '结论';
  if (entry.type === 'project_completed') return '完成';
  return entry.type;
}
</script>

<template>
  <div class="space-y-3">
    <button
      v-for="entry in entries"
      :key="entry.id"
      type="button"
      class="w-full rounded-2xl border px-3 py-3 text-left transition"
      :class="selectedEntryId === entry.id ? 'border-brand-300 bg-brand-50/70' : 'border-slate-200 bg-white hover:bg-slate-50'"
      @click="emit('open', entry)"
    >
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <BadgePill :tone="toneFor(entry)">{{ labelFor(entry) }}</BadgePill>
            <span class="text-[11px] text-slate-400">{{ new Date(entry.timestamp).toLocaleString('zh-CN') }}</span>
          </div>
          <div class="mt-2 text-sm font-medium text-slate-900">{{ entry.title }}</div>
          <div v-if="entry.meta.length" class="mt-2 space-y-1 text-xs text-slate-500">
            <div v-for="line in entry.meta" :key="line">{{ line }}</div>
          </div>
        </div>
        <div class="text-[11px] text-slate-400">{{ entry.actor }}</div>
      </div>
    </button>
  </div>
</template>
