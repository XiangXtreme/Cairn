<script setup lang="ts">
import { storeToRefs } from 'pinia';

import { useUiStore } from '@/stores/ui';

const ui = useUiStore();
const { toast } = storeToRefs(ui);
</script>

<template>
  <div class="pointer-events-none fixed bottom-5 right-5 z-50">
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div
        v-if="toast.show"
        class="pointer-events-auto rounded-2xl border px-4 py-3 text-sm shadow-soft"
        :class="[
          toast.type === 'success' && 'border-emerald-200 bg-emerald-50 text-emerald-800',
          toast.type === 'error' && 'border-rose-200 bg-rose-50 text-rose-800',
          toast.type === 'info' && 'border-slate-200 bg-white text-slate-700',
        ]"
      >
        {{ toast.message }}
      </div>
    </transition>
  </div>
</template>
