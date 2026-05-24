<script setup lang="ts">
import { ArrowLeft, CheckCheck, CirclePlay, Copy, FileCode2, Lightbulb, PauseCircle, Pencil, RefreshCcw, Sparkles, TicketPlus, Trash2 } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import type { ProjectDetail } from '@/types/workspace';
import { projectStatusTone } from '@/utils/workspace';

defineProps<{
  project: ProjectDetail;
  replayActive?: boolean;
}>();

const emit = defineEmits<{
  back: [];
  toggleStatus: [];
  hint: [];
  complete: [];
  rename: [];
  clone: [];
  reopen: [];
  delete: [];
  yaml: [];
  intent: [];
  replay: [];
}>();
</script>

<template>
  <section class="rounded-[28px] border border-slate-200 bg-white p-4 shadow-sm">
    <div class="flex flex-col gap-4 2xl:flex-row 2xl:items-center 2xl:justify-between">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="truncate text-xl font-semibold text-slate-950">{{ project.project.title }}</h2>
          <BadgePill :tone="projectStatusTone(project.project.status)">{{ project.project.status }}</BadgePill>
        </div>
        <div class="mt-1 text-xs font-mono text-slate-400">{{ project.project.id }}</div>
        </div>

      <div class="flex flex-wrap items-center gap-2">
        <AppButton :icon="ArrowLeft" size="sm" variant="ghost" @click="emit('back')">返回列表</AppButton>
        <AppButton :icon="Sparkles" size="sm" variant="brand" :disabled="replayActive" @click="emit('intent')">创建意图</AppButton>
        <AppButton :icon="TicketPlus" size="sm" :disabled="replayActive" @click="emit('replay')">回放</AppButton>
        <AppButton :icon="Lightbulb" size="sm" :disabled="replayActive" @click="emit('hint')">加 Hint</AppButton>
        <AppButton :icon="FileCode2" size="sm" @click="emit('yaml')">导出</AppButton>
        <AppButton :icon="Pencil" size="sm" :disabled="replayActive" @click="emit('rename')">重命名</AppButton>
        <AppButton :icon="Copy" size="sm" :disabled="replayActive" @click="emit('clone')">克隆</AppButton>
        <AppButton
          v-if="project.project.status === 'completed'"
          :icon="RefreshCcw"
          size="sm"
          :disabled="replayActive"
          @click="emit('reopen')"
        >
          重新打开
        </AppButton>
        <AppButton
          v-else
          :icon="project.project.status === 'active' ? PauseCircle : CirclePlay"
          size="sm"
          :disabled="replayActive"
          @click="emit('toggleStatus')"
        >
          {{ project.project.status === 'active' ? '暂停' : '恢复' }}
        </AppButton>
        <AppButton
          v-if="project.project.status !== 'completed'"
          :icon="CheckCheck"
          size="sm"
          :disabled="replayActive"
          @click="emit('complete')"
        >
          标记完成
        </AppButton>
        <AppButton :icon="Trash2" size="sm" variant="danger" :disabled="replayActive" @click="emit('delete')">删除</AppButton>
      </div>
    </div>
  </section>
</template>
