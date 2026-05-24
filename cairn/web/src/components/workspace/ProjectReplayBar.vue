<script setup lang="ts">
import { Pause, Play, RotateCcw, SkipForward, X } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import type { ReplayState } from '@/types/workspace';

defineProps<{
  replay: ReplayState;
}>();

const emit = defineEmits<{
  toggle: [];
  restart: [];
  advance: [];
  exit: [];
}>();
</script>

<template>
  <section v-if="replay.active" class="rounded-[28px] border border-violet-200 bg-violet-50/70 p-4 shadow-sm">
    <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-violet-600">回放</div>
        <div class="mt-1 text-sm font-medium text-slate-900">
          帧 {{ replay.frameIndex + 1 }} / {{ replay.frames.length }}
          <span class="ml-2 text-slate-500">{{ replay.playing ? '播放中' : '已暂停' }}</span>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <AppButton :icon="replay.playing ? Pause : Play" size="sm" variant="brand" @click="emit('toggle')">
          {{ replay.playing ? '暂停' : '播放' }}
        </AppButton>
        <AppButton :icon="SkipForward" size="sm" @click="emit('advance')">下一帧</AppButton>
        <AppButton :icon="RotateCcw" size="sm" @click="emit('restart')">重播</AppButton>
        <AppButton :icon="X" size="sm" variant="danger" @click="emit('exit')">退出回放</AppButton>
      </div>
    </div>
  </section>
</template>
