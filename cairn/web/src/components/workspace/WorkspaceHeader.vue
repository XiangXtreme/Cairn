<script setup lang="ts">
import { FolderKanban, PauseCircle, Plus, Settings, Waves } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';

defineProps<{
  projectCount: number;
  selectedProjectTitle?: string;
}>();

const emit = defineEmits<{
  create: [];
  settings: [];
  pauseAll: [];
}>();
</script>

<template>
  <header class="border-b border-slate-200/80 bg-white/95 backdrop-blur">
    <div class="px-5 py-4 lg:px-8">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            <Waves class="h-3.5 w-3.5" />
            <span>Cairn Workspace</span>
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-3">
            <h1 class="text-2xl font-semibold tracking-tight text-slate-950">
              {{ selectedProjectTitle || '项目工作台' }}
            </h1>
            <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
              <FolderKanban class="h-3.5 w-3.5" />
              {{ projectCount }} 个项目
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <AppButton :icon="Plus" variant="brand" @click="emit('create')">新建项目</AppButton>
          <AppButton :icon="PauseCircle" @click="emit('pauseAll')">暂停全部活跃项目</AppButton>
          <AppButton :icon="Settings" @click="emit('settings')">设置</AppButton>
        </div>
      </div>
    </div>
  </header>
</template>
