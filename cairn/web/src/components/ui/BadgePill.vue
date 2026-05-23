<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: 'slate' | 'brand' | 'teal' | 'rose' | 'amber' | 'sky';
  }>(),
  {
    tone: 'slate',
  },
);
</script>

<template>
  <span
    class="inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]"
    :class="[
      tone === 'slate' && 'border-slate-200 bg-slate-100 text-slate-500',
      tone === 'brand' && 'border-brand-200 bg-brand-50 text-brand-700',
      tone === 'teal' && 'border-teal-200 bg-teal-50 text-teal-700',
      tone === 'rose' && 'border-rose-200 bg-rose-50 text-rose-700',
      tone === 'amber' && 'border-amber-200 bg-amber-50 text-amber-700',
      tone === 'sky' && 'border-sky-200 bg-sky-50 text-sky-700',
    ]"
  >
    <slot />
  </span>
</template>
