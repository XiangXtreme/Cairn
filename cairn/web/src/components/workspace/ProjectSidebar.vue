<script setup lang="ts">
import { BookText, CheckCheck, CircleDot, Lightbulb, ListTree, Network, Radio, RotateCcw, Send } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import TextInput from '@/components/ui/TextInput.vue';
import type { Intent, ProjectDetail, SideTab, TimelineEntry } from '@/types/workspace';
import ProjectTimeline from './ProjectTimeline.vue';

const props = defineProps<{
  project: ProjectDetail;
  sideTab: SideTab;
  selectedFactId?: string | null;
  selectedIntentId?: string | null;
  selectedTimelineEntryId?: string | null;
  entries: TimelineEntry[];
  actorName: string;
  sidePanelWidth: number;
  replayActive?: boolean;
}>();

const emit = defineEmits<{
  tab: [tab: SideTab];
  timeline: [entry: TimelineEntry];
  selectFact: [factId: string];
  selectIntent: [intentId: string];
  updateActorName: [value: string | number | null];
  claimIntent: [intentId: string];
  releaseIntent: [intentId: string];
  concludeIntent: [intentId: string];
}>();

const tabs: Array<{ id: SideTab; label: string; icon: typeof BookText }> = [
  { id: 'detail', label: '节点', icon: Network },
  { id: 'timeline', label: '时间线', icon: BookText },
  { id: 'hints', label: '提示', icon: Lightbulb },
  { id: 'intents', label: '意图', icon: ListTree },
];

function intentTone(intent: Intent) {
  if (intent.to) return 'teal';
  if (intent.worker) return 'amber';
  return 'slate';
}

function intentStatus(intent: Intent) {
  if (intent.to) return '已结论';
  if (intent.worker) return intent.worker;
  return '未认领';
}

function canClaim(intent: Intent) {
  return !intent.to && !intent.worker;
}

function canRelease(intent: Intent) {
  return !intent.to && intent.worker === props.actorName;
}

function canConclude(intent: Intent) {
  return !intent.to && intent.worker === props.actorName;
}
</script>

<template>
  <aside class="flex h-full min-h-[620px] flex-col rounded-[28px] border border-slate-200 bg-slate-50 shadow-sm">
    <div class="border-b border-slate-200 px-3 py-3">
      <div class="mb-3 rounded-2xl border border-slate-200 bg-white px-3 py-3">
        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">本地偏好</div>
        <div class="mt-3 space-y-3">
          <div>
            <div class="mb-1 text-xs text-slate-500">执行者名称</div>
            <TextInput :model-value="actorName" @update:model-value="emit('updateActorName', $event)" />
          </div>
          <div class="text-[11px] text-slate-400">侧栏宽度 {{ sidePanelWidth }}px</div>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-2">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="flex flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px] font-medium transition"
          :class="sideTab === tab.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:bg-white/70'"
          @click="emit('tab', tab.id)"
        >
          <component :is="tab.icon" class="h-4 w-4" />
          <span>{{ tab.label }}</span>
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-3 py-3">
      <div v-if="sideTab === 'detail'" class="space-y-3">
        <article v-if="selectedFactId || selectedIntentId" class="rounded-2xl border border-brand-200 bg-brand-50/60 p-3">
          <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-700">当前选中</div>
          <div class="mt-2 text-sm text-slate-800">
            <template v-if="selectedFactId">事实 {{ selectedFactId }}</template>
            <template v-else-if="selectedIntentId">意图 {{ selectedIntentId }}</template>
          </div>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-3">
          <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">事实</div>
          <div class="mt-3 space-y-2">
            <button
              v-for="fact in project.facts"
              :key="fact.id"
              type="button"
              class="block w-full rounded-2xl border px-3 py-2 text-left transition hover:bg-slate-50"
              :class="selectedFactId === fact.id ? 'border-brand-300 bg-brand-50/70' : 'border-slate-200'"
              @click="emit('selectFact', fact.id)"
            >
              <div class="flex items-center gap-2">
                <BadgePill tone="sky">{{ fact.id }}</BadgePill>
              </div>
              <div class="mt-2 text-sm text-slate-700">{{ fact.description }}</div>
            </button>
          </div>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-3">
          <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">意图</div>
          <div class="mt-3 space-y-2">
            <button
              v-for="intent in project.intents"
              :key="intent.id"
              type="button"
              class="block w-full rounded-2xl border px-3 py-2 text-left transition hover:bg-slate-50"
              :class="selectedIntentId === intent.id ? 'border-brand-300 bg-brand-50/70' : 'border-slate-200'"
              @click="emit('selectIntent', intent.id)"
            >
              <div class="flex items-center gap-2">
                <BadgePill :tone="intentTone(intent)">{{ intent.id }}</BadgePill>
                <span class="text-xs text-slate-400">{{ intentStatus(intent) }}</span>
              </div>
              <div class="mt-2 text-sm text-slate-700">{{ intent.description }}</div>
              <div v-if="!intent.to" class="mt-3 flex flex-wrap gap-2">
                <AppButton v-if="canClaim(intent)" :icon="Send" size="sm" :disabled="replayActive" @click.stop="emit('claimIntent', intent.id)">认领</AppButton>
                <AppButton v-if="canRelease(intent)" :icon="Radio" size="sm" :disabled="replayActive" @click.stop="emit('claimIntent', intent.id)">心跳</AppButton>
                <AppButton v-if="canRelease(intent)" :icon="RotateCcw" size="sm" :disabled="replayActive" @click.stop="emit('releaseIntent', intent.id)">释放</AppButton>
                <AppButton v-if="canConclude(intent)" :icon="CheckCheck" size="sm" variant="brand" :disabled="replayActive" @click.stop="emit('concludeIntent', intent.id)">结论</AppButton>
              </div>
            </button>
          </div>
        </article>
      </div>

      <ProjectTimeline
        v-else-if="sideTab === 'timeline'"
        :entries="entries"
        :selected-entry-id="selectedTimelineEntryId"
        @open="emit('timeline', $event)"
      />

      <div v-else-if="sideTab === 'hints'" class="space-y-2">
        <article v-for="hint in project.hints" :key="hint.id" class="rounded-2xl border border-slate-200 bg-white p-3">
          <div class="flex items-center gap-2">
            <BadgePill tone="amber">{{ hint.id }}</BadgePill>
            <span class="text-[11px] text-slate-400">{{ hint.creator }}</span>
          </div>
          <div class="mt-2 text-sm text-slate-700">{{ hint.content }}</div>
        </article>
      </div>

      <div v-else class="space-y-2">
        <article v-for="intent in project.intents" :key="intent.id" class="rounded-2xl border border-slate-200 bg-white p-3">
          <div class="flex items-center gap-2">
            <BadgePill :tone="intentTone(intent)">{{ intent.id }}</BadgePill>
            <span class="text-[11px] text-slate-400">{{ intent.from.join(', ') }}</span>
          </div>
          <div class="mt-2 text-sm text-slate-700">{{ intent.description }}</div>
          <div class="mt-2 text-xs text-slate-400">{{ intentStatus(intent) }}</div>
          <div v-if="!intent.to" class="mt-3 flex flex-wrap gap-2">
            <AppButton v-if="canClaim(intent)" :icon="Send" size="sm" :disabled="replayActive" @click="emit('claimIntent', intent.id)">认领</AppButton>
            <AppButton v-if="canRelease(intent)" :icon="Radio" size="sm" :disabled="replayActive" @click="emit('claimIntent', intent.id)">心跳</AppButton>
            <AppButton v-if="canRelease(intent)" :icon="RotateCcw" size="sm" :disabled="replayActive" @click="emit('releaseIntent', intent.id)">释放</AppButton>
            <AppButton v-if="canConclude(intent)" :icon="CheckCheck" size="sm" variant="brand" :disabled="replayActive" @click="emit('concludeIntent', intent.id)">结论</AppButton>
          </div>
        </article>
      </div>
    </div>
  </aside>
</template>
