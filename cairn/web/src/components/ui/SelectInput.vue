<script setup lang="ts">
defineProps<{
  modelValue: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  change: [];
}>();

function onChange(event: Event) {
  emit('update:modelValue', (event.target as HTMLSelectElement).value);
  emit('change');
}
</script>

<template>
  <select
    :value="modelValue"
    :disabled="disabled"
    class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 transition focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
    @change="onChange"
  >
    <slot />
  </select>
</template>
