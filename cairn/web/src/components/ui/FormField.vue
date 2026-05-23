<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string;
    hint?: string;
  }>(),
  {
    hint: '',
  },
);
</script>

<template>
  <label class="block min-w-0">
    <span class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">{{ label }}</span>
    <slot />
    <p v-if="hint" class="mt-1 text-[11px] leading-5 text-slate-400">{{ hint }}</p>
  </label>
</template>
