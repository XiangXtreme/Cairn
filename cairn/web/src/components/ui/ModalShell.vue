<script setup lang="ts">
import { X } from 'lucide-vue-next';

defineProps<{
  title: string;
  description?: string;
  wide?: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6" @click.self="emit('close')">
    <div
      class="max-h-[90vh] w-full overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl"
      :class="wide ? 'max-w-4xl' : 'max-w-xl'"
    >
      <header class="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
        <div class="min-w-0">
          <h3 class="text-lg font-semibold text-slate-900">{{ title }}</h3>
          <p v-if="description" class="mt-1 text-sm text-slate-500">{{ description }}</p>
        </div>
        <button
          type="button"
          class="inline-flex h-10 w-10 items-center justify-center rounded-2xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          @click="emit('close')"
        >
          <X class="h-5 w-5" />
        </button>
      </header>
      <div class="max-h-[calc(90vh-88px)] overflow-y-auto">
        <slot />
      </div>
    </div>
  </div>
</template>
