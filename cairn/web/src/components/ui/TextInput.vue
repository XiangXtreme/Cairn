<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: string | number | null;
    type?: string;
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    type: 'text',
    placeholder: '',
    disabled: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null];
}>();

function onInput(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.type === 'number') {
    emit('update:modelValue', input.value === '' ? null : Number(input.value));
    return;
  }
  emit('update:modelValue', input.value);
}
</script>

<template>
  <input
    :type="type"
    :value="modelValue ?? ''"
    :placeholder="placeholder"
    :disabled="disabled"
    class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 transition placeholder:text-slate-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
    @input="onInput"
  />
</template>
