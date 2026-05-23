<script setup lang="ts">
import type { Component } from 'vue';

withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'brand' | 'danger' | 'ghost';
    size?: 'sm' | 'md';
    icon?: Component;
    disabled?: boolean;
    type?: 'button' | 'submit';
  }>(),
  {
    variant: 'secondary',
    size: 'md',
    disabled: false,
    type: 'button',
  },
);
</script>

<template>
  <button
    :type="type"
    :disabled="disabled"
    class="inline-flex items-center justify-center gap-2 rounded-2xl font-medium transition disabled:cursor-not-allowed disabled:opacity-40"
    :class="[
      size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm',
      variant === 'primary' && 'bg-slate-900 text-white shadow-sm hover:bg-slate-800',
      variant === 'brand' && 'bg-brand-500 text-white shadow-sm shadow-brand-200 hover:bg-brand-600',
      variant === 'secondary' && 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
      variant === 'danger' && 'border border-rose-200 bg-white text-rose-600 hover:bg-rose-50',
      variant === 'ghost' && 'text-slate-500 hover:bg-slate-100',
    ]"
  >
    <component :is="icon" v-if="icon" class="h-4 w-4" aria-hidden="true" />
    <slot />
  </button>
</template>
